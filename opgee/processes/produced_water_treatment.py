from ..log import getLogger
from ..process import Process
from ..energy import EN_ELECTRICITY
from ..stream import Stream, PHASE_GAS, PHASE_LIQUID, PHASE_SOLID
from ..error import OpgeeException
from opgee import ureg

_logger = getLogger(__name__)


class ProducedWaterTreatment(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")
        self.oil_volume_rate = field.attr("oil_prod")
        self.WOR = field.attr("WOR")
        self.WIR = field.attr("WIR")

        self.water_reinjection = field.attr("water_reinjection")
        self.water_flooding = field.attr("water_flooding")
        self.frac_water_reinj = field.attr("fraction_water_reinjected")

        self.steam_flooding = field.attr("steam_flooding")
        self.SOR = field.attr("SOR")
        self.steam_quality_outlet = field.attr("steam_quality_at_generator_outlet")
        self.steam_quality_blowdown = field.attr("steam_quality_after_blowdown")

        self.frac_disp_subsurface = self.attr("fraction_disp_water_subsurface")
        self.frac_disp_surface = self.attr("fraction_disp_water_surface")

        self.water_treatment_table = self.model.water_treatment
        self.num_stages = self.attr("number_of_stages")
        self.stages = sorted(self.water_treatment_table.index.unique())

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        input = self.find_input_streams("water", combine=True)
        total_water_mass_rate = input.liquid_flow_rate("H2O")

        water = self.field.water
        water_density = water.density(input.temperature, input.pressure)
        total_water_volume = total_water_mass_rate / water_density

        if self.num_stages > len(self.stages) or self.num_stages < 0:
            raise OpgeeException(f"produced water treatment: number of stages must be <= {len(self.stages)}")

        electricity = 0
        for stage in self.stages[:self.num_stages]:
            stage_row = self.water_treatment_table.loc[stage]
            electricity_factor = (stage_row["Apply"].squeeze() *
                                  stage_row["EC"].squeeze()).sum()
            electricity += electricity_factor * total_water_volume
            loss_factor = (stage_row["Apply"].squeeze() *
                           stage_row["Volume loss"].squeeze()).sum()
            total_water_volume *= (1 - loss_factor)

        total_water_inj_demand = 0
        if self.water_reinjection:
            total_water_inj_demand = min(self.oil_volume_rate * self.WOR * self.frac_water_reinj, total_water_volume)
        elif self.water_flooding:
            total_water_inj_demand = min(self.oil_volume_rate * self.WIR, total_water_volume)
        frac_prod_water_as_water = 1 if total_water_inj_demand > total_water_volume else \
            total_water_inj_demand / total_water_volume

        if self.steam_flooding:
            total_steam_inj_demand = min(self.oil_volume_rate * self.SOR / self.steam_quality_outlet,
                                         total_water_inj_demand - total_water_volume)
        else:
            total_steam_inj_demand = ureg.Quantity(0, "m**3/day")
        frac_prod_water_as_steam = 1 if total_steam_inj_demand > total_water_volume else \
            total_steam_inj_demand / total_water_volume

        steam_inj_CWE_rate = self.SOR * self.oil_volume_rate if self.steam_flooding else 0
        steam_inj_mass_rate = steam_inj_CWE_rate * water.density()
        water_mass_blowdown = (steam_inj_mass_rate *
                               (self.steam_quality_blowdown - self.steam_quality_outlet) / self.steam_quality_outlet)
        water_required = water_mass_blowdown + steam_inj_mass_rate

        output_steam = self.find_output_stream("water for steam", raiseError=False)

        if self.steam_flooding:
            water_available = frac_prod_water_as_steam * total_water_mass_rate
            steam_rate = (water_required if water_available > water_required else water_available)
        else:
            steam_rate = ureg.Quantity(0, "tonne/day")
        # steam rate is frac*tonne/day
        output_steam.set_liquid_flow_rate("H2O", steam_rate.to("tonne/day"), t=input.temperature, p=input.pressure)

        output_reinjection = self.find_output_stream("water for reinjection")
        reinjection_rate = frac_prod_water_as_water * total_water_mass_rate
        output_reinjection.set_liquid_flow_rate("H2O", reinjection_rate.to("tonne/day"),
                                                t=input.temperature, p=input.pressure)

        output_surface_disposal = self.find_output_stream("water for surface disposal")
        water_for_disp = (1 - frac_prod_water_as_steam - frac_prod_water_as_water) * total_water_mass_rate
        surface_disp_rate = water_for_disp * self.frac_disp_surface + steam_rate
        # surface disp rate is frac*tonne/day
        output_surface_disposal.set_liquid_flow_rate("H2O", surface_disp_rate.to("tonne/day"),
                                                     t=self.std_temp, p=self.std_press)

        output_subsurface_disposal = self.find_output_stream("water for subsurface disposal")
        subsurface_disp_rate = water_for_disp * self.frac_disp_subsurface
        # subsurface disp rate is frac*tonne/day
        output_subsurface_disposal.set_liquid_flow_rate("H2O", subsurface_disp_rate.to("tonne/day"),
                                                        t=input.temperature, p=input.pressure)

        # enegy use
        energy_use = self.energy
        energy_use.set_rate(EN_ELECTRICITY, electricity.to("mmBtu/day"))

        # emission
        emissions = self.emissions
