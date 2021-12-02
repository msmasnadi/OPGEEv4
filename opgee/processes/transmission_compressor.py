from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID, PHASE_GAS
from opgee.stream import Stream
from ..config import getParam
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
from .. import ureg
from ..compressor import Compressor
from ..energy import Energy, EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
from ..emissions import Emissions, EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES

_logger = getLogger(__name__)


class TransmissionCompressor(Process):
    """
    Transmission compressor calculate compressor emissions after the production site boundary

    """

    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        # self.gas_boundary = field.attr("gas_boundary")
        self.press_drop_per_dist = self.attr("press_drop_per_dist")
        self.transmission_dist = self.attr("transmission_dist")
        self.transmission_freq = self.attr("transmission_freq")
        self.transmission_inlet_press = self.attr("transmission_inlet_press")
        self.prime_mover_type = self.attr("prime_mover_type")
        self.eta_compressor = self.attr("eta_compressor")

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas")

        if input.is_empty():
                return

        # Transmission system properties
        station_outlet_press = self.press_drop_per_dist * self.transmission_freq + self.transmission_inlet_press

        # initial compressor properties
        overall_compression_ratio = station_outlet_press / input.pressure
        compression_ratio = Compressor.get_compression_ratio(overall_compression_ratio)
        num_stages = Compressor.get_num_of_compression(overall_compression_ratio)
        total_work, outlet_temp = Compressor.get_compressor_work_temp(self.field,
                                                                      input.temperature,
                                                                      input.pressure,
                                                                      input,
                                                                      compression_ratio,
                                                                      num_stages)
        volume_flow_rate_STP = self.gas.tot_volume_flow_rate_STP(input)
        total_energy = total_work * volume_flow_rate_STP
        brake_horse_power = total_energy / self.eta_compressor
        energy_consumption = self.get_energy_consumption(self.prime_mover_type, brake_horse_power)

        energy_consumption = Compressor.get_compressor_energy_consumption(self.field,
                                                                          self.prime_mover_type,
                                                                          self.eta_compressor,
                                                                          overall_compression_ratio,
                                                                          input)

        # Along-pipeline booster compressor properties


        # # energy-use
        # energy_use = self.energy
        # if self.prime_mover_type == "NG_engine" or "NG_turbine":
        #     energy_carrier = EN_NATURAL_GAS
        # elif self.prime_mover_type == "Electric_motor":
        #     energy_carrier = EN_ELECTRICITY
        # else:
        #     energy_carrier = EN_DIESEL
        # energy_use.set_rate(energy_carrier, energy_consumption)

        # # emissions
        # emissions = self.emissions
        # energy_for_combustion = energy_use.data.drop("Electricity")
        # combustion_emission = (energy_for_combustion * self.process_EF).sum()
        # emissions.add_rate(EM_COMBUSTION, "CO2", combustion_emission)
        #
        # # emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)



