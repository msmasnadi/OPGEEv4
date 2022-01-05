from opgee import ureg
from ..log import getLogger
from ..process import Process
from ..stream import Stream, PHASE_GAS
from ..compressor import Compressor
from ..emissions import EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES

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
        self.eta_compressor_lifting = field.attr("eta_compressor_lifting")
        self.prime_mover_type_gas_lifting = field.attr("prime_mover_type_gas_lifting")

        self.amb_temp = self.field.model.const("std-temperature")
        self.amb_press = self.field.model.const("std-pressure")

    def run(self, analysis):
        self.print_running_msg()
        # mass rate

        input = self.find_input_stream("gas")
        temp = input.temperature
        press = input.pressure

        if input.is_empty():
            return

        methane_lifting = self.field.get_process_data(
            "methane_from_gas_lifting") if self.gas_lifting else None
        gas_lifting_fugitive_loss_rate = self.field.get_process_data("gas_lifting_compressor_loss_rate")
        gas_stream = self.get_gas_lifting_init_stream(self.imported_fuel_gas_comp,
                                                      self.imported_fuel_gas_mass_fracs,
                                                      self.GLIR, self.oil_prod,
                                                      self.water_prod, temp, press)
        if methane_lifting is None and len(gas_stream.gas_flow_rates()) > 0:
            discharge_press = (self.res_press + press) / 2 + ureg.Quantity(100, "psi")
            overall_compression_ratio = discharge_press / press
            compression_ratio = Compressor.get_compression_ratio(overall_compression_ratio)
            num_stages = Compressor.get_num_of_compression(overall_compression_ratio)
            total_work, _ = Compressor.get_compressor_work_temp(self.field, temp, press, gas_stream, compression_ratio,
                                                                num_stages)
            volume_flow_rate_STP = self.gas.tot_volume_flow_rate_STP(gas_stream)
            total_energy = total_work * volume_flow_rate_STP
            brake_horse_power = total_energy / self.eta_compressor_lifting
            energy_consumption = self.get_energy_consumption(self.prime_mover_type_gas_lifting, brake_horse_power)
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
        gas_to_vent.copy_flow_rates_from(input)
        gas_to_vent.multiply_flow_rates(venting_frac.m)
        gas_to_vent.set_temperature_and_pressure(self.amb_temp, self.amb_press)

        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(input)
        gas_fugitives.multiply_flow_rates(fugitive_frac.m)
        gas_fugitives.set_temperature_and_pressure(self.amb_temp, self.amb_press)

        gas_to_gathering = self.find_output_stream("gas for gas gathering")
        gas_to_gathering.copy_flow_rates_from(input)
        gas_to_gathering.multiply_flow_rates(1 - venting_frac.m - fugitive_frac.m)
        gas_to_gathering.set_temperature_and_pressure(input.temperature, input.pressure)

        self.set_iteration_value(gas_to_vent.total_flow_rate() +
                                 gas_fugitives.total_flow_rate() +
                                 gas_to_gathering.total_flow_rate())

        # emissions
        emissions = self.emissions
        emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)
        emissions.add_from_stream(EM_VENTING, gas_to_vent)

    # def generate_gas_lifting_stream(self, temp, press):
    #     """
    #
    #     :param temp:
    #     :param press:
    #     :return:
    #     """
    #     stream = Stream("gas lifting stream", temperature=temp, pressure=press)
    #     gas_lifting_series = self.imported_fuel_gas_mass_fracs * \
    #                          self.GLIR * (self.oil_prod + self.water_prod) \
    #                          * self.gas.component_gas_rho_STP[self.imported_fuel_gas_comp.index]
    #     stream.set_rates_from_series(gas_lifting_series, PHASE_GAS)
    #     return stream
