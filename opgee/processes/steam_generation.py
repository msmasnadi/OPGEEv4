from ..log import getLogger
from ..process import Process
from ..error import BalanceError
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_UPG_PROC_GAS, EN_PETCOKE
from ..emissions import EM_COMBUSTION

_logger = getLogger(__name__)

# the tolerance is used for checking mass and energy balance
# (input - output) / input < tolerance
tolerance = 0.01


class SteamGeneration(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.steam_flooding_check = field.attr("steam_flooding")

        if self.steam_flooding_check != 1:
            self.enabled = False
            return

        self.SOR = field.attr("SOR")
        self.oil_volume_rate = field.attr("oil_prod")
        self.steam_quality_outlet = field.attr("steam_quality_outlet")
        self.steam_quality_after_blowdown = field.attr("steam_quality_after_blowdown")
        self.fraction_blowdown_recycled = field.attr("fraction_blowdown_recycled")
        self.waste_water_reinjection_temp = field.attr("waste_water_reinjection_temp")
        self.waste_water_reinjection_press = field.attr("waste_water_reinjection_press")
        self.friction_loss_stream_distr = field.attr("friction_loss_stream_distr")
        self.pressure_loss_choke_wellhead = field.attr("pressure_loss_choke_wellhead")
        self.water = field.water
        self.water_density = self.water.density()
        self.res_press = field.attr("res_press")
        self.steam_press_upper = field.model.const("steam-press-upper-limit")
        self.steam_injection_delta_press = field.attr("steam_injection_delta_press")
        self.steam_generator_press_outlet = min((self.res_press + self.steam_injection_delta_press) *
                                                self.friction_loss_stream_distr *
                                                self.pressure_loss_choke_wellhead, self.steam_press_upper)
        self.steam_generator_temp_outlet = self.water.saturated_temperature(self.steam_generator_press_outlet)
        self.prod_water_inlet_press = field.attr("prod_water_inlet_press")
        self.makeup_water_inlet_press = field.attr("makeup_water_inlet_press")
        self.eta_displacementpump_steamgen = field.attr("eta_displacementpump_steamgen")
        self.eta_air_blower_OTSG = field.attr("eta_air_blower_OTSG")
        self.eta_air_blower_HRSG = field.attr("eta_air_blower_HRSG")
        self.eta_air_blower_solar = field.attr("eta_air_blower_solar")
        self.steam_generator = field.steam_generator

    def run(self, analysis):
        self.print_running_msg()
        self.set_iteration_value(0)

        # mass rate
        steam_injection_volume_rate = self.SOR * self.oil_volume_rate
        water_mass_rate_for_injection = steam_injection_volume_rate * self.water_density
        blowdown_water_mass_rate = water_mass_rate_for_injection * (
                self.steam_quality_after_blowdown - self.steam_quality_outlet) / self.steam_quality_outlet
        waste_water_from_blowdown = blowdown_water_mass_rate * (1 - self.fraction_blowdown_recycled)
        recycled_blowdown_water = blowdown_water_mass_rate * self.fraction_blowdown_recycled

        output_waster_water = self.find_output_stream("waste water")
        output_waster_water.set_liquid_flow_rate("H2O",
                                                 waste_water_from_blowdown.to("tonne/day"),
                                                 self.waste_water_reinjection_temp,
                                                 self.waste_water_reinjection_press)
        output_recycled_blowdown_water = self.find_output_stream("blowdown water")
        output_recycled_blowdown_water.set_liquid_flow_rate("H2O", recycled_blowdown_water.to("tonne/day"),
                                                            self.waste_water_reinjection_temp,
                                                            self.waste_water_reinjection_press)

        input_prod_water = self.find_input_stream("produced water for steam generation")
        prod_water_mass_rate = input_prod_water.liquid_flow_rate("H2O")

        input_makeup_water = self.find_input_stream("makeup water for steam generation")
        makeup_water_mass_rate = input_makeup_water.liquid_flow_rate("H2O")

        makeup_water_to_prod_water_frac = makeup_water_mass_rate / prod_water_mass_rate

        fuel_consumption_OTSG, mass_in_OTSG, mass_out_OTSG, energy_in_OTSG, energy_out_OTSG = \
            self.steam_generator.once_through_SG(prod_water_mass_rate,
                                                 makeup_water_mass_rate,
                                                 water_mass_rate_for_injection,
                                                 blowdown_water_mass_rate)
        fuel_consumption_HRSG, electricity_HRSG, mass_in_HRSG, mass_out_HRSG, energy_in_HRSG, energy_out_HRSG = \
            self.steam_generator.heat_recovery_SG(prod_water_mass_rate,
                                                  makeup_water_mass_rate,
                                                  water_mass_rate_for_injection,
                                                  blowdown_water_mass_rate)

        fuel_consumption_solar = self.steam_generator.solar_SG(prod_water_mass_rate, makeup_water_mass_rate)

        # check balance
        if abs(mass_in_OTSG.to("kg/day").m - mass_out_OTSG.to("kg/day").m) / mass_in_OTSG.to("kg/day").m > tolerance:
            raise BalanceError(self.name, "OTSG_mass")
        elif abs(mass_in_HRSG.to("kg/day").m - mass_out_HRSG.to("kg/day").m) / mass_in_HRSG.to("kg/day").m > tolerance:
            raise BalanceError(self.name, "HRSG_mass")
        elif abs(energy_in_OTSG.to("MJ/day").m - energy_out_OTSG.to("MJ/day").m) / energy_in_OTSG.to(
                "MJ/day").m > tolerance:
            raise BalanceError(self.name, "OTSG_energy")
        elif abs(energy_in_HRSG.to("MJ/day").m - energy_out_HRSG.to("MJ/day").m) / energy_in_HRSG.to(
                "MJ/day").m > tolerance:
            raise BalanceError(self.name, "HRSG_energy")

        # energy use
        energy_use = self.energy
        NG_consumption = fuel_consumption_OTSG + fuel_consumption_HRSG + fuel_consumption_solar
        energy_use.set_rate(EN_NATURAL_GAS, NG_consumption.to("mmBtu/day"))

        water_pump_hp = self.get_feedwater_horsepower(steam_injection_volume_rate, makeup_water_to_prod_water_frac)
        water_pump_power = self.get_energy_consumption("Electric_motor", water_pump_hp)
        OTSG_air_blower = self.get_energy_consumption("Electric_motor",
                                                      fuel_consumption_OTSG * self.eta_air_blower_OTSG)
        HRSG_air_blower = self.get_energy_consumption("Electric_motor",
                                                      fuel_consumption_HRSG * self.eta_air_blower_HRSG)
        solar_thermal_pumping = self.get_energy_consumption("Electric_motor",
                                                            fuel_consumption_solar * self.eta_air_blower_solar)
        total_power_required = water_pump_power + OTSG_air_blower + HRSG_air_blower + solar_thermal_pumping
        energy_use.set_rate(EN_ELECTRICITY, total_power_required - electricity_HRSG.to("mmBtu/day"))

        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "CO2", combustion_emission)

    def get_feedwater_horsepower(self, steam_injection_volume_rate, makeup_water_to_prod_water_frac):
        result = steam_injection_volume_rate * makeup_water_to_prod_water_frac * (
                self.steam_generator_press_outlet - self.makeup_water_inlet_press) + \
                 steam_injection_volume_rate * (1 - makeup_water_to_prod_water_frac) * (
                         self.steam_generator_press_outlet - self.prod_water_inlet_press)
        result /= self.eta_displacementpump_steamgen

        return result
