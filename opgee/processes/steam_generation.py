#
# SteamGeneration class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .. import ureg
from ..core import TemperaturePressure
from ..emissions import EM_COMBUSTION
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY
from ..error import BalanceError
from ..import_export import WATER
from ..log import getLogger
from ..process import Process
from .shared import get_energy_consumption

_logger = getLogger(__name__)

# the tolerance is used for checking mass and energy balance
# (input - output) / input < tolerance
tolerance = 0.01


class SteamGeneration(Process):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.SOR = None
        self.eta_air_blower_HRSG = None
        self.eta_air_blower_OTSG = None
        self.eta_air_blower_solar = None
        self.eta_displacement_pump = None
        self.fraction_OTSG = None
        self.fraction_blowdown_recycled = None
        self.fraction_steam_cogen = None
        self.fraction_steam_solar = None
        self.friction_loss_steam_distr = None
        self.makeup_water_inlet_press = None
        self.oil_volume_rate = None
        self.pressure_loss_choke_wellhead = None
        self.prod_water_inlet_press = None
        self.res_press = None
        self.steam_flooding_check = None
        self.steam_generator = None
        self.steam_generator_press_outlet = None
        self.steam_injection_delta_press = None
        self.steam_quality_after_blowdown = None
        self.steam_quality_outlet = None
        self.waste_water_reinjection_tp = None
        self.water_density = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field
        self.steam_flooding_check = field.steam_flooding
        self.SOR = field.SOR
        self.oil_volume_rate = field.oil_volume_rate
        self.steam_quality_outlet = self.attr("steam_quality_outlet")
        self.steam_quality_after_blowdown = self.attr("steam_quality_after_blowdown")
        self.fraction_blowdown_recycled = self.attr("fraction_blowdown_recycled")

        self.waste_water_reinjection_tp = TemperaturePressure(self.attr("waste_water_reinjection_temp"),
                                                              self.attr("waste_water_reinjection_press"))

        self.pressure_loss_choke_wellhead = self.attr("pressure_loss_choke_wellhead")
        self.friction_loss_steam_distr = field.friction_loss_steam_distr
        self.water_density = self.water.density()
        self.res_press = field.res_press
        self.steam_injection_delta_press = self.attr("steam_injection_delta_press")
        self.steam_generator_press_outlet = ((self.res_press + self.steam_injection_delta_press) *
                                             self.friction_loss_steam_distr *
                                             self.pressure_loss_choke_wellhead)
        self.prod_water_inlet_press = self.attr("prod_water_inlet_press")
        self.makeup_water_inlet_press = self.attr("makeup_water_inlet_press")
        self.eta_displacement_pump = self.attr("eta_displacement_pump")
        self.eta_air_blower_OTSG = self.attr("eta_air_blower_OTSG")
        self.eta_air_blower_HRSG = self.attr("eta_air_blower_HRSG")
        self.eta_air_blower_solar = self.attr("eta_air_blower_solar")

        self.fraction_steam_cogen = field.fraction_steam_cogen
        self.fraction_steam_solar = field.fraction_steam_solar
        self.fraction_OTSG = 1 - self.fraction_steam_cogen - self.fraction_steam_solar

        # TODO: the SteamGenerator is instantiated only here, in Field, yet it is used only
        #       in the SteamGeneration process. Is the SteamGenerator intended to be used by
        #       other processes? If not, this, why not move its methods into SteamGeneration?
        #       The only methods SteamGenerator called in SteamGeneration are called once each,
        #       in run().
        self.steam_generator = field.steam_generator

    def check_enabled(self):
        # TODO: Don't silently edit the user's model: raise an error instead.
        if self.steam_flooding_check != 1 or self.SOR == 0:
            self.set_enabled(False)

    def run(self, analysis):
        self.print_running_msg()
        self.set_iteration_value(0)
        field = self.field
        import_product = field.import_export

        # mass rate

        input_prod_water = self.find_input_stream("produced water for steam generation")
        input_makeup_water = self.find_input_stream("makeup water for steam generation")
        if input_prod_water.is_uninitialized() and input_makeup_water.is_uninitialized():
            return

        prod_water_mass_rate = input_prod_water.liquid_flow_rate("H2O")
        makeup_water_mass_rate = input_makeup_water.liquid_flow_rate("H2O")
        water_mass_rate_for_injection = prod_water_mass_rate + makeup_water_mass_rate
        steam_injection_volume_rate = water_mass_rate_for_injection / self.water_density

        steam_quality_diff_between_blowndown_and_outlet = self.steam_quality_after_blowdown - self.steam_quality_outlet
        steam_quality_diff_between_blowndown_and_outlet = \
            ureg.Quantity(max(steam_quality_diff_between_blowndown_and_outlet.to("frac").m, 0.0), "frac")

        if steam_quality_diff_between_blowndown_and_outlet.m < 0:
            _logger.warning(f"steam quality after blowdown is smaller than steam quality at outlet")

        blowdown_water_mass_rate = \
            water_mass_rate_for_injection * steam_quality_diff_between_blowndown_and_outlet / self.steam_quality_outlet
        waste_water_from_blowdown = blowdown_water_mass_rate * (1 - self.fraction_blowdown_recycled)
        import_product.set_export(self.name, WATER, waste_water_from_blowdown)

        recycled_blowdown_water = blowdown_water_mass_rate * self.fraction_blowdown_recycled

        recycled_water_stream = self.find_output_stream("recycled water")
        recycled_water_stream.set_liquid_flow_rate("H2O",
                                                   recycled_blowdown_water.to("tonne/day"),
                                                   tp=self.waste_water_reinjection_tp)

        fuel_consumption_OTSG = fuel_consumption_HRSG = fuel_consumption_solar = \
            electricity_HRSG = ureg.Quantity(0, "MJ/day")

        fraction_OTSG = self.fraction_OTSG
        if fraction_OTSG.m != 0:
            fuel_consumption_OTSG, mass_in_OTSG, mass_out_OTSG, energy_in_OTSG, energy_out_OTSG = \
                self.steam_generator.once_through_SG(prod_water_mass_rate * fraction_OTSG,
                                                     makeup_water_mass_rate * fraction_OTSG,
                                                     water_mass_rate_for_injection * fraction_OTSG,
                                                     blowdown_water_mass_rate * fraction_OTSG)
            self.check_balance(mass_in_OTSG, mass_out_OTSG, "OTSG_mass")
            self.check_balance(energy_in_OTSG, energy_out_OTSG, "OTSG_energy")

        fraction_steam_cogen = self.fraction_steam_cogen
        if self.fraction_steam_cogen != 0:
            fuel_consumption_HRSG, electricity_HRSG, mass_in_HRSG, mass_out_HRSG, energy_in_HRSG, energy_out_HRSG = \
                self.steam_generator.heat_recovery_SG(prod_water_mass_rate * fraction_steam_cogen,
                                                      makeup_water_mass_rate * fraction_steam_cogen,
                                                      water_mass_rate_for_injection * fraction_steam_cogen,
                                                      blowdown_water_mass_rate * fraction_steam_cogen)
            self.check_balance(mass_in_HRSG, mass_out_HRSG, "HRSG_mass")
            self.check_balance(energy_in_HRSG, energy_out_HRSG, "HRSG_energy")

        if self.fraction_steam_solar != 0:
            fuel_consumption_solar = \
                self.steam_generator.solar_SG(prod_water_mass_rate * self.fraction_steam_solar,
                                              makeup_water_mass_rate * self.fraction_steam_solar)

        # energy use
        energy_use = self.energy
        NG_consumption = fuel_consumption_OTSG + fuel_consumption_HRSG
        energy_use.set_rate(EN_NATURAL_GAS, NG_consumption.to("mmBtu/day"))

        water_pump_hp = self.get_feedwater_horsepower(prod_water_mass_rate, makeup_water_mass_rate)
        water_pump_power = get_energy_consumption("Electric_motor", water_pump_hp)
        OTSG_air_blower = get_energy_consumption("Electric_motor",
                                                 fuel_consumption_OTSG * self.eta_air_blower_OTSG)
        HRSG_air_blower = get_energy_consumption("Electric_motor",
                                                 fuel_consumption_HRSG * self.eta_air_blower_HRSG)
        solar_thermal_pumping = get_energy_consumption("Electric_motor",
                                                       fuel_consumption_solar * self.eta_air_blower_solar)
        total_power_required = water_pump_power + OTSG_air_blower + HRSG_air_blower + solar_thermal_pumping
        energy_use.set_rate(EN_ELECTRICITY, total_power_required)

        # import/export
        self.set_import_from_energy(energy_use)
        import_product = field.import_export
        import_product.set_export(self.name, EN_ELECTRICITY, electricity_HRSG)

        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)

    def get_feedwater_horsepower(self, prod_water_mass_rate, makeup_water_mass_rate):
        prod_water_volume_rate = prod_water_mass_rate / self.water_density
        makeup_water_mass_rate = makeup_water_mass_rate / self.water_density

        result = makeup_water_mass_rate * (self.steam_generator_press_outlet - self.makeup_water_inlet_press) + \
                 prod_water_volume_rate * (self.steam_generator_press_outlet - self.prod_water_inlet_press)
        result /= self.eta_displacement_pump

        return result

    def check_balance(self, input, output, label):
        """

        :param input:
        :param output:
        :param label:
        :return:
        """

        unit = input.units
        if abs(input.m - output.to(unit).m) > tolerance * input.m:
            raise BalanceError(self.name, label)
