from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID, PHASE_GAS
from opgee.stream import Stream
from ..config import getParam
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
from .. import ureg

_logger = getLogger(__name__)


class GasPartition(Process):
    """
    Gas partition is to check the reasonable amount of gas goes to gas lifting and gas reinjection

    """
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")
        self.gas_lifting = field.attr("gas_lifting")
        self.imported_fuel_gas_comp = field.attrs_with_prefix("imported_gas_comp_")
        self.imported_fuel_gas_mass_fracs = field.gas.component_mass_fractions(self.imported_fuel_gas_comp)
        self.imported_gas_stream = Stream("imported_gas", temperature=self.std_temp, pressure=self.std_press)
        self.imported_gas_stream.set_rates_from_series(self.imported_fuel_gas_mass_fracs * ureg.Quantity(1, "tonne/day"),
                                                  phase=PHASE_GAS)
        self.GLIR = field.attr("GLIR")
        self.oil_prod = field.attr("oil_prod")
        self.WOR = field.attr("WOR")
        self.water_prod = self.oil_prod * self.WOR
        self.is_first_loop = True

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_streams("gas for gas partition", combine=True)
        temp = input.temperature
        press = input.pressure

        gas_lifting = self.find_output_stream("lifting gas")

        if self.gas_lifting:
            if self.is_first_loop:
                init_stream = self.get_gas_lifting_init_stream(self.imported_fuel_gas_comp,
                                                      self.imported_fuel_gas_mass_fracs,
                                                      self.GLIR, self.oil_prod,
                                                      self.water_prod, temp, press)
                gas_lifting.copy_flow_rates_from(init_stream)
                self.is_first_loop = False
            else:
                gas_lifting.copy_flow_rates_from(input)
                self.field.save_process_data(methane_from_gas_lifting=gas_lifting.gas_flow_rate("C1"))

        gas_lifting.set_temperature_and_pressure(input.temperature, input.pressure)
        # Check
        # self.set_iteration_value(output.total_flow_rate())
        def test_diff(input_stream, output_stream, name):
            diff = output_stream.gas_flow_rate(name) - input_stream.gas_flow_rate(name)
            return diff if diff.m >= 0 else 0

        # iteration_tuple = [test_diff(input, gas_lifting, name) for name in Stream.emission_composition]
        iteration_series = (gas_lifting.components.gas - input.components.gas).astype(float)
        iteration_series[iteration_series < 0] = 0
        self.set_iteration_value(iteration_series)

        # TODO: How does the iteration value or tuple be calculated, how to check convergence
        if not self.iteration_converged:
            return
        gas_to_reinjection = self.find_output_stream("gas for gas reinjection compressor")
        gas_to_reinjection.copy_flow_rates_from(input)
        gas_to_reinjection.subtract_gas_rates_from(gas_lifting)

        # exported gas can have negative flow rates which means the imported gas
        exported_gas = self.find_output_stream("gas for export")

        excluded = [s.strip() for s in getParam("OPGEE.ExcludeFromReinjectionEnergySummary").split(",")]
        energy_sum = self.field.sum_process_energy(processes_to_exclude=excluded)
        NG_energy_sum = energy_sum.get_rate(EN_NATURAL_GAS)

        NG_LHV = self.gas.mass_energy_density(gas_to_reinjection)
        is_gas_to_reinjection_empty = False
        if NG_LHV.m == 0:
            is_gas_to_reinjection_empty = True
            NG_LHV = self.gas.mass_energy_density(self.imported_gas_stream)
        NG_mass = NG_energy_sum / NG_LHV
        NG_consumption_stream = Stream(name="NG_consump_stream",
                                       temperature=gas_to_reinjection.temperature,
                                       pressure=gas_to_reinjection.pressure)
        if is_gas_to_reinjection_empty:
            NG_consumption_series = self.imported_fuel_gas_mass_fracs * NG_mass
        else:
            NG_consumption_series = self.gas.component_mass_fractions(self.gas.component_molar_fractions(gas_to_reinjection)) * NG_mass
        NG_consumption_stream.set_rates_from_series(NG_consumption_series, PHASE_GAS)

        exported_gas.copy_flow_rates_from(gas_to_reinjection)
        exported_gas.subtract_gas_rates_from(NG_consumption_stream)
        gas_to_reinjection.subtract_gas_rates_from(exported_gas)


