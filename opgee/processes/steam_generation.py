from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID

_logger = getLogger(__name__)


class SteamGeneration(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.steam_flooding_check = field.attr("steam_flooding")

        if self.steam_flooding_check != 1:
            self.enabled = False
            return

        self.frac_steam_cogen = field.attr("fraction_steam_cogen")
        self.frac_steam_solar = field.attr("fraction_steam_solar")
        self.imported_gas_comp = self.attrs_with_prefix("imported_gas_comp_")
        self.NG_fuel_share_OTSG_produced = self.attr("NG_fuel_share_OTSG_produced")
        self.NG_fuel_share_HRSG_produced = self.attr("NG_fuel_share_HRSG_produced")
        self.SOR = field.attr("SOR")
        self.oil_volume_rate = field.attr("oil_prod")
        self.steam_quality_outlet = self.attr("steam_quality_outlet")
        self.steam_quality_after_blowdown = self.attr("steam_quality_after_blowdown")
        self.fraction_blowdown_recycled = self.attr("fraction_blowdown_recycled")
        self.waste_water_reinjection_temp = self.attr("waste_water_reinjection_temp")
        self.waste_water_reinjection_press = self.attr("waste_water_reinjection_press")
        self.friction_loss_stream_distr = self.attr("friction_loss_stream_distr")
        self.pressure_loss_choke_wellhead = self.attr("pressure_loss_choke_wellhead")

        self.water = self.field.water
        self.water_density = self.water.density()

        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")

        self.res_press = field.attr("res_press")
        self.steam_press_upper = field.model.const("steam-press-upper-limit")
        self.steam_injection_delta_press = self.attr("steam_injection_delta_press")
        self.steam_generator_press_outlet = min((self.res_press+self.steam_injection_delta_press)*
                                                self.friction_loss_stream_distr*
                                                self.pressure_loss_choke_wellhead, self.steam_press_upper)
        self.steam_generator_temp_outlet = self.water.saturated_temperature(self.steam_generator_press_outlet)

    def run(self, analysis):
        self.print_running_msg()
        self.set_iteration_value(0)

        # mass rate
        steam_injection_volume_rate = self.SOR * self.oil_volume_rate
        water_mass_rate_for_injection = steam_injection_volume_rate * self.water_density
        blowdown_water_mass_rate = water_mass_rate_for_injection * (self.steam_quality_after_blowdown - self.steam_quality_outlet) / self.steam_quality_outlet
        waste_water_from_blowdown = blowdown_water_mass_rate * (1-self.fraction_blowdown_recycled)
        recycled_blowdown_water = blowdown_water_mass_rate * self.fraction_blowdown_recycled

        output_waster_water = self.find_output_stream("waste water")
        output_waster_water.set_liquid_flow_rate("H2O", waste_water_from_blowdown.to("tonne/day"), self.waste_water_reinjection_temp, self.waste_water_reinjection_press)
        output_recycled_blowdown_water = self.find_output_stream("blowdown water")
        output_recycled_blowdown_water.set_liquid_flow_rate("H2O", recycled_blowdown_water.to("tonne/day"), self.waste_water_reinjection_temp, self.waste_water_reinjection_press)

        # output_steam_injection = self.find_output_stream("water for steam injection")
        # output_steam_injection.set_liquid_flow_rate("H2O", water_mass_rate_for_injection.to("tonne/day"), self.steam_generator_temp_outlet, self.steam_generator_press_outlet)

        input_prod_water = self.find_input_stream("produced water for steam generation")
        input_makeup_water = self.find_input_stream("makeup water for steam generation")

