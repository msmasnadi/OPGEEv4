from ..log import getLogger
from ..process import Process
from ..energy import EN_ELECTRICITY
from ..stream import Stream, PHASE_GAS, PHASE_LIQUID, PHASE_SOLID
from opgee import ureg

_logger = getLogger(__name__)


class ProducedWaterTreatment(Process):
    def run(self, analysis):
        self.print_running_msg()

        field = self.get_field()
        std_temp = field.model.const("std-temperature")
        std_press = field.model.const("std-pressure")
        oil_volume_rate = field.attr("oil_prod")
        WOR = field.attr("WOR")
        WIR = field.attr("WIR")

        water_reinjection = field.attr("water_reinjection")
        water_flooding = field.attr("water_flooding")
        frac_water_reinj = field.attr("fraction_water_reinjected")

        steam_flooding = field.attr("steam_flooding")
        SOR = field.attr("SOR")
        steam_quality_outlet = self.attr("steam_quality_at_generator_outlet")
        steam_quality_blowdown = self.attr("steam_quality_after_blowdown")

        frac_disp_subsurface = self.attr("fraction_disp_water_subsurface")
        frac_disp_surface = self.attr("fraction_disp_water_surface")

        water_treatment_table = self.model.water_treatment

        # mass rate
        input = self.find_input_streams("water", combine=True)
        total_water_mass_rate = input.liquid_flow_rate("H2O")

        water = field.water
        water_density = water.density(input.temperature, input.pressure)
        total_water_volume = total_water_mass_rate / water_density
        stages = ["Stage 1", "Stage 2", "Stage 3", "Stage 4"]  # TODO: define in the xml
        electricity = 0
        for stage in stages:
            stage_row = water_treatment_table.loc[stage]
            electricity_factor = (stage_row["Apply"].squeeze() *
                                  stage_row["EC"].squeeze()).sum()
            electricity += electricity_factor * total_water_volume
            loss_factor = (stage_row["Apply"].squeeze() *
                           stage_row["Volume loss"].squeeze()).sum()
            total_water_volume *= (1 - loss_factor)

        total_water_inj_demand = 0
        if water_reinjection:
            total_water_inj_demand = min(oil_volume_rate * WOR * frac_water_reinj, total_water_volume)
        elif water_flooding:
            total_water_inj_demand = min(oil_volume_rate * WIR, total_water_volume)
        frac_prod_water_as_water = 1 if total_water_inj_demand > total_water_volume else \
            total_water_inj_demand / total_water_volume


        if steam_flooding:
            total_steam_inj_demand = min(oil_volume_rate * SOR / steam_quality_outlet,
                                         total_water_inj_demand - total_water_volume)
        else:
            total_steam_inj_demand = ureg.Quantity(0, "m**3/day")
        frac_prod_water_as_steam = 1 if total_steam_inj_demand > total_water_volume else \
            total_steam_inj_demand / total_water_volume

        steam_inj_CWE_rate = SOR * oil_volume_rate if steam_flooding else 0
        steam_inj_mass_rate = steam_inj_CWE_rate * water.density()
        water_mass_blowdown = (steam_inj_mass_rate *
                               (steam_quality_blowdown - steam_quality_outlet) / steam_quality_outlet)
        water_required = water_mass_blowdown + steam_inj_mass_rate

        output_steam = self.find_output_stream("water for steam", raiseError=False)

        if steam_flooding:
            water_available = frac_prod_water_as_steam * total_water_mass_rate
            steam_rate = (water_required if water_available > water_required else water_available)
        else:
            steam_rate = ureg.Quantity(0, "tonne/day")
        output_steam.set_liquid_flow_rate("H2O", steam_rate, t=input.temperature, p=input.pressure)

        output_reinjection = self.find_output_stream("water for reinjection")
        reinjection_rate = frac_prod_water_as_water * total_water_mass_rate
        output_reinjection.set_liquid_flow_rate("H2O", reinjection_rate, t=input.temperature, p=input.pressure)

        output_surface_disposal = self.find_output_stream("water for surface disposal")
        surface_disp_rate = ((1 - frac_prod_water_as_steam - frac_prod_water_as_water) *
                             total_water_mass_rate * frac_disp_surface) + steam_rate
        # surface disp rate is frac*tonne/day
        output_surface_disposal.set_liquid_flow_rate("H2O", surface_disp_rate.to("tonne/day"), t=std_temp, p=std_press)

        output_subsurface_disposal = self.find_output_stream("water for subsurface disposal")
        subsurface_disp_rate = ((1 - frac_prod_water_as_steam - frac_prod_water_as_water) *
                                total_water_mass_rate * frac_disp_subsurface)
        output_subsurface_disposal.set_liquid_flow_rate("H2O", subsurface_disp_rate.to("tonne/day"),
                                                        t=input.temperature, p=input.pressure)

        # enegy use
        energy_use = self.energy
        energy_use.set_rate(EN_ELECTRICITY, electricity.to("mmBtu/day"))

        # emission
        emissions = self.emissions
