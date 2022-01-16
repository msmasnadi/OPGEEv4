from .. import ureg
from opgee.processes.compressor import Compressor
from ..emissions import EM_VENTING, EM_FUGITIVES
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class Venting(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.pipe_leakage = field.attr("surface_piping_leakage")
        self.gas_lifting = field.attr("gas_lifting")
        self.VOR = field.attr("VOR")
        self.GOR = field.attr("GOR")
        self.WOR = field.attr("WOR")
        self.GLIR = field.attr("GLIR")
        self.oil_prod = field.attr("oil_prod")
        self.res_press = field.attr("res_press")
        self.water_prod = self.oil_prod * self.WOR
        self.VOR_over_GOR = self.VOR / self.GOR
        self.imported_fuel_gas_comp = field.attrs_with_prefix("imported_gas_comp_")
        self.imported_fuel_gas_mass_fracs = field.gas.component_mass_fractions(self.imported_fuel_gas_comp)

    def run(self, analysis):
        self.print_running_msg()
        field = self.field
        # mass rate

        input = self.find_input_stream("gas")
        input_temp = input.temperature
        input_press = input.pressure

        if input.is_uninitialized():
            return

        methane_lifting = self.field.get_process_data(
            "methane_from_gas_lifting") if self.gas_lifting else None
        gas_lifting_fugitive_loss_rate = self.field.get_process_data("gas_lifting_compressor_loss_rate")
        gas_stream = self.get_gas_lifting_init_stream(self.imported_fuel_gas_comp,
                                                      self.imported_fuel_gas_mass_fracs,
                                                      self.GLIR, self.oil_prod,
                                                      self.water_prod, input_temp, input_press)
        if methane_lifting is None and len(gas_stream.gas_flow_rates()) > 0:
            discharge_press = (self.res_press + input_press) / 2 + ureg.Quantity(100, "psi")
            overall_compression_ratio = discharge_press / input_press
            energy_consumption, _, _ = Compressor.get_compressor_energy_consumption(field,
                                                                                    field.prime_mover_type_lifting,
                                                                                    field.eta_compressor_lifting,
                                                                                    overall_compression_ratio,
                                                                                    gas_stream,
                                                                                    inlet_temp=input.temperature,
                                                                                    inlet_pressure=input.pressure)
            energy_content_imported_gas = self.gas.mass_energy_density(gas_stream) * gas_stream.total_gas_rate()
            frac_imported_gas_consumed = energy_consumption / energy_content_imported_gas
            loss_rate = (ureg.Quantity(0, "frac")
                         if gas_lifting_fugitive_loss_rate is None else gas_lifting_fugitive_loss_rate)
            factor = 1 - loss_rate - frac_imported_gas_consumed
            gas_stream.multiply_flow_rates(factor.m)
            methane_lifting = gas_stream.gas_flow_rate("C1")

        methane_to_venting = (input.gas_flow_rate("C1") - methane_lifting) * self.VOR_over_GOR
        venting_frac = methane_to_venting / input.gas_flow_rate("C1")
        fugitive_frac = self.pipe_leakage / input.gas_flow_rate("C1")

        if self.field.get_process_data("gas_lifting_stream") is None:
            self.field.save_process_data(gas_lifting_stream=gas_stream)

        gas_to_vent = self.find_output_stream("gas venting")
        gas_to_vent.copy_flow_rates_from(input, temp=field.std_temp, press=field.std_press)
        gas_to_vent.multiply_flow_rates(venting_frac.m)

        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(input, temp=field.std_temp, press=field.std_press)
        gas_fugitives.multiply_flow_rates(fugitive_frac.m)

        gas_to_gathering = self.find_output_stream("gas for gas gathering")
        gas_to_gathering.copy_flow_rates_from(input)
        gas_to_gathering.multiply_flow_rates(1 - venting_frac.m - fugitive_frac.m)
        gas_to_gathering.set_temperature_and_pressure(input.temperature, input.pressure)

        self.set_iteration_value(gas_to_vent.total_flow_rate() +
                                 gas_fugitives.total_flow_rate() +
                                 gas_to_gathering.total_flow_rate())

        # emissions
        emissions = self.emissions
        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
        emissions.set_from_stream(EM_VENTING, gas_to_vent)
