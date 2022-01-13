from .. import ureg
from .shared import get_energy_carrier
from ..compressor import Compressor
from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class CO2ReinjectionCompressor(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.std_temp = field.model.const("std-temperature")
        # TODO: remove field.xx to field.py and change the reference
        self.std_press = field.model.const("std-pressure")
        self.res_press = field.attr("res_press")
        self.eta_compressor = self.attr("eta_compressor")
        self.prime_mover_type = self.attr("prime_mover_type")

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        input = self.find_input_streams("gas for CO2 compressor", combine=True)

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)
        gas_fugitives.set_temperature_and_pressure(self.std_temp, self.std_press)

        gas_to_well = self.find_output_stream("gas for CO2 injection well")
        gas_to_well.copy_flow_rates_from(input)
        gas_to_well.subtract_gas_rates_from(gas_fugitives)

        discharge_press = self.res_press + ureg.Quantity(500, "psi")
        overall_compression_ratio = discharge_press / input.pressure
        energy_consumption, temp, _ = Compressor.get_compressor_energy_consumption(self.field,
                                                                                   self.prime_mover_type,
                                                                                   self.eta_compressor,
                                                                                   overall_compression_ratio,
                                                                                   input)

        gas_to_well.set_temperature_and_pressure(temp, input.pressure)

        self.field.save_process_data(CO2_injection_rate=gas_to_well.gas_flow_rate("CO2"))

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, energy_consumption)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "CO2", combustion_emission)

        emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)
