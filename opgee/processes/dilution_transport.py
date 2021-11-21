import pandas as pd

from ..process import Process
from ..log import getLogger
from .. import ureg
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_UPG_PROC_GAS, EN_PETCOKE, EN_DIESEL, EN_RESID
from ..emissions import EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES

_logger = getLogger(__name__)


class DiluentTransport(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.oil = field.oil

        self.API_diluent = field.attr("diluent_API")
        self.transport_share_fuel = field.model.transport_share_fuel
        self.ocean_tanker_load_factor_dest = field.attr("ocean_tanker_load_factor_dest")
        self.barge_load_factor_dest = field.attr("barge_load_factor_dest")
        self.ocean_tanker_load_factor_origin = field.attr("ocean_tanker_load_factor_origin")
        self.barge_load_factor_origin = field.attr("barge_load_factor_origin")
        self.ocean_tanker_size = field.attr("ocean_tanker_size")
        self.barge_capacity = field.attr("barge_capacity")
        self.ocean_tanker_speed = field.attr("ocean_tanker_speed")
        self.barge_speed = field.attr("barge_speed")
        self.energy_intensity_pipeline_turbine = field.attr("energy_intensity_pipeline_turbine")
        self.frac_power_pipeline_turbine = field.attr("frac_power_pipeline_turbine")
        self.energy_intensity_pipeline_engine_current = field.attr("energy_intensity_pipeline_engine_current")
        self.frac_power_pipeline_engine_current = field.attr("frac_power_pipeline_engine_current")
        self.energy_intensity_pipeline_engine_future = field.attr("energy_intensity_pipeline_engine_future")
        self.frac_power_pipeline_engine_future = field.attr("frac_power_pipeline_engine_future")
        self.energy_intensity_rail_transport = field.attr("energy_intensity_rail_transport")
        self.energy_intensity_truck = field.attr("energy_intensity_truck")
        self.fraction_transport = field.attrs_with_prefix("fraction_diluent_transport_")
        self.transport_distance = field.attrs_with_prefix("diluent_transport_distance_")
        self.losses_feed = field.attr("losses_feed")

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("oil for transport")

        if input.is_empty():
            return

        oil_mass_rate = input.liquid_flow_rate("oil")
        oil_mass_energy_density = self.oil.mass_energy_density(self.API_diluent)
        oil_LHV_rate = oil_mass_rate * oil_mass_energy_density

        ocean_tanker_dest_energy_consumption = self.get_water_transport_energy_consumption(
            self.ocean_tanker_load_factor_dest, "tanker")
        ocean_tanker_orig_energy_consumption = self.get_water_transport_energy_consumption(
            self.ocean_tanker_load_factor_origin, "tanker")
        barge_dest_energy_consumption = self.get_water_transport_energy_consumption(self.barge_load_factor_dest,
                                                                                    "barge")
        barge_orig_energy_consumption = self.get_water_transport_energy_consumption(self.barge_load_factor_origin,
                                                                                    "barge")

        ocean_tanker_hp = ureg.Quantity(9070 + 0.101 * self.ocean_tanker_size.m, "hp")
        barge_hp = ureg.Quantity(5600 / 22500 * self.barge_capacity.m, "hp")

        ocean_tanker_dest_energy_intensity = self.transport_energy_intensity("tanker",
                                                                             ocean_tanker_dest_energy_consumption,
                                                                             self.ocean_tanker_load_factor_dest,
                                                                             ocean_tanker_hp)
        barge_dest_energy_intensity = self.transport_energy_intensity("barge",
                                                                      barge_dest_energy_consumption,
                                                                      self.barge_load_factor_dest,
                                                                      barge_hp)
        pipeline_dest_energy_intensity = (self.energy_intensity_pipeline_turbine * self.frac_power_pipeline_turbine +
                                          self.energy_intensity_pipeline_engine_current * self.frac_power_pipeline_engine_current +
                                          self.energy_intensity_pipeline_engine_future * self.frac_power_pipeline_engine_future)
        rail_dest_energy_intensity = self.energy_intensity_rail_transport
        truck_dest_energy_intensity = self.energy_intensity_truck

        ocean_tanker_origin_energy_intensity = self.transport_energy_intensity("tanker",
                                                                               ocean_tanker_orig_energy_consumption,
                                                                               self.ocean_tanker_load_factor_origin,
                                                                               ocean_tanker_hp)
        barge_origin_energy_intensity = self.transport_energy_intensity("barge", barge_orig_energy_consumption,
                                                                        self.barge_load_factor_origin, barge_hp)
        pipeline_origin_energy_intensity = ureg.Quantity(0, "btu/tonne/mile")
        rail_origin_energy_intensity = ureg.Quantity(200, "btu/tonne/mile")
        truck_origin_energy_intensity = self.energy_intensity_truck

        transport_dest_energy_consumption = pd.Series([ocean_tanker_dest_energy_intensity, barge_dest_energy_intensity,
                                                       pipeline_dest_energy_intensity, rail_dest_energy_intensity,
                                                       truck_dest_energy_intensity], dtype="pint[btu/tonne/mile]")
        transport_origin_energy_consumption = pd.Series(
            [ocean_tanker_origin_energy_intensity, barge_origin_energy_intensity,
             pipeline_origin_energy_intensity, rail_origin_energy_intensity,
             truck_origin_energy_intensity], dtype="pint[btu/tonne/mile]")

        final_diluent_LHV_mass = self.field.get_process_data("final_diluent_LHV_mass")
        transport_energy_consumption = (transport_dest_energy_consumption + transport_origin_energy_consumption) / \
                                       final_diluent_LHV_mass

        # energy use
        energy_use = self.energy
        NG_consumption = self.fuel_consumption(transport_energy_consumption, oil_LHV_rate, "Natural gas")
        diesel_consumption = self.fuel_consumption(transport_energy_consumption, oil_LHV_rate, "Diesel") + self.losses_feed * oil_LHV_rate
        residual_fuel_consumption = self.fuel_consumption(transport_energy_consumption, oil_LHV_rate, "Residual oil")
        electricity = self.fuel_consumption(transport_energy_consumption, oil_LHV_rate, "Electricity")
        energy_use.set_rate(EN_NATURAL_GAS, NG_consumption.to("mmBtu/day"))
        energy_use.set_rate(EN_DIESEL, diesel_consumption.to("mmBtu/day"))
        energy_use.set_rate(EN_RESID, residual_fuel_consumption.to("mmBtu/day"))
        energy_use.set_rate(EN_ELECTRICITY, electricity.to("mmBtu/day"))

        # emission
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combusion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "CO2", combusion_emission)

    def impute(self):
        output = self.find_output_stream("oil for dilution")
        input = self.find_input_stream("oil for transport")
        input.copy_flow_rates_from(output)
        input.set_temperature_and_pressure(output.temperature, output.pressure)

    def transport_energy_intensity(self, type, energy_consumption, load_factor, hp):
        """
        calculate tanker energy intensity using load factor

        :param type: (str) "tanker" or "barge"
        :param hp:
        :param energy_consumption:
        :param load_factor:
        :return: (float) tanker energy intensity
        """
        if type == "tanker":
            result = energy_consumption * load_factor * hp / self.ocean_tanker_speed / self.ocean_tanker_size
        else:
            result = energy_consumption * load_factor * hp / self.barge_capacity / self.barge_speed
        return result

    def fuel_consumption(self, transport_energy_consumption, LHV, type):
        """
        calculate different type of fuel consumption

        :param type: (str) fuel type such as Natural gas, Diesel, etc.
        :param transport_energy_consumption:
        :param LHV:
        :return: (float) calculate fuel consumption
        """
        transport_energy_consumption.index = self.transport_distance.index

        result = (transport_energy_consumption * self.transport_distance * self.fraction_transport *
                          self.transport_share_fuel[type]).sum() * LHV
        return result
