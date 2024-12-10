#
# WaterTreatment class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..core import TemperaturePressure
from ..energy import EN_ELECTRICITY
from ..error import OpgeeException
from ..import_export import WATER
from ..log import getLogger
from ..process import Process
from ..units import ureg

_logger = getLogger(__name__)


class WaterTreatment(Process):
    """
        The water treatment process ...

        Inputs:
            - A

        Outputs:
            - B
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self._required_inputs = [
            "water",
        ]

        self._required_outputs = []

        field = self.field
        if field.steam_flooding:
            self._required_outputs.extend([
                "makeup water",
                "produced water",
            ])

        if field.water_flooding or field.water_reinjection:
            self._required_outputs.append("water")

        self.water_treatment_table = self.model.water_treatment

        self.SOR = None
        self.WIR = None
        self.frac_disp_subsurface = None
        self.frac_disp_surface = None
        self.frac_water_reinj = None
        self.makeup_water_tp = None
        self.makeup_water_treatment = None
        self.makeup_water_treatment_tbl = None
        self.num_stages = None
        self.oil_volume_rate = None
        self.steam_flooding = None
        self.steam_quality_blowdown = None
        self.steam_quality_outlet = None
        self.water_density_STP = None
        self.water_flooding = None
        self.water_reinjection = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field
        self.oil_volume_rate = field.oil_volume_rate
        self.WIR = field.WIR

        self.water_reinjection = field.water_reinjection
        self.water_flooding = field.water_flooding
        self.frac_water_reinj = field.frac_water_reinj
        self.water_density_STP = field.water.density()

        self.steam_flooding = field.steam_flooding
        self.SOR = field.SOR
        self.steam_quality_outlet = self.attr("steam_quality_at_generator_outlet")
        self.steam_quality_blowdown = self.attr("steam_quality_after_blowdown")

        self.frac_disp_subsurface = self.attr("fraction_disp_water_subsurface")
        self.frac_disp_surface = self.attr("fraction_disp_water_surface")

        self.makeup_water_treatment = None
        self.makeup_water_treatment_tbl = self.attr("makeup_water_treatment_table")

        self.makeup_water_tp = TemperaturePressure(self.attr("makeup_water_temp"),
                                                   self.attr("makeup_water_press"))

        self.num_stages = self.attr("number_of_stages")

        self.init_intermediate_results(["Produced Water", "Makeup Water"])

    def run(self, analysis):
        """
        Run the WaterTreatment process.

        :param analysis: (opgee.Analysis)
        :return: nothing
        """
        self.print_running_msg()
        field = self.field

        self.WOR = field.attr("WOR")

        # mass rate
        input = self.find_input_streams("water", combine=True)
        if input.is_uninitialized():
            return

        input_water_mass_rate = input.liquid_flow_rate("H2O")

        # Water reinjection and water flooding are mutually exclusive
        injected_water_vol_demand = ureg.Quantity(0.0, "barrel_water/day")
        if self.water_reinjection:
            injected_water_vol_demand = self.oil_volume_rate * self.WOR * self.frac_water_reinj
        elif self.water_flooding:
            injected_water_vol_demand = self.oil_volume_rate * self.WIR

        injected_steam_vol_demand = ureg.Quantity(0.0, "barrel_water/day")
        if self.steam_flooding:
            injected_steam_vol_demand = self.oil_volume_rate * self.SOR

        injected_water_mass_demand = injected_water_vol_demand * self.water_density_STP
        injected_steam_mass_demand = injected_steam_vol_demand * self.water_density_STP

        makeup_water_mass = max(injected_water_mass_demand - input_water_mass_rate, ureg.Quantity(0.0, "tonne/day"))
        prod_water_mass = min(injected_water_mass_demand, input_water_mass_rate)

        makeup_steam_mass =\
            max(injected_steam_mass_demand - input_water_mass_rate + prod_water_mass,
                ureg.Quantity(0.0, "tonne/day"))
        prod_steam_mass =\
            min(injected_steam_mass_demand, input_water_mass_rate - prod_water_mass)

        if self.steam_flooding:
            makeup_water_to_steam = self.find_output_stream("makeup water")
            prod_water_to_steam = self.find_output_stream("produced water")
            prod_water_to_steam.set_liquid_flow_rate("H2O", prod_steam_mass.to("tonne/day"), tp=input.tp)
            if makeup_steam_mass.m != 0:
                makeup_water_to_steam.set_liquid_flow_rate("H2O", makeup_steam_mass.to("tonne/day"),
                                                           tp=self.makeup_water_tp)
        if self.water_flooding or self.water_reinjection:
            water_to_reinjection = self.find_output_stream("water")
            water_to_reinjection_rate = prod_water_mass + makeup_water_mass
            water_to_reinjection.set_liquid_flow_rate("H2O", water_to_reinjection_rate, tp=input.tp)

        water_for_disp =\
            input_water_mass_rate - makeup_water_mass - makeup_steam_mass - prod_water_mass - prod_steam_mass
        self.set_iteration_value(water_for_disp)

        surface_disp_rate = water_for_disp * self.frac_disp_surface
        subsurface_disp_rate = water_for_disp * self.frac_disp_subsurface

        water_density = field.water.density() # water is under the standard conditions
        input_water_volume_rate = input_water_mass_rate / water_density
        makeup_water_vol_downstream = (makeup_water_mass + makeup_steam_mass) / water_density

        # energy use
        prod_water_elec = self.get_water_treatment_elec(self.water_treatment_table, input_water_volume_rate)
        if self.makeup_water_treatment_tbl:
            makeup_water_table = self.water_treatment_table
        else:
            if self.makeup_water_treatment is None:
                raise OpgeeException("no makeup water table provided")
            else:
                makeup_water_table = self.makeup_water_treatment
        makeup_water_elec = self.get_water_treatment_elec(makeup_water_table, makeup_water_vol_downstream)

        energy_use_prod, emissions_prod = self.intermediate_results["Produced Water"]
        energy_use_makeup, emissions_makeup = self.intermediate_results["Makeup Water"]
        energy_use_prod.set_rate(EN_ELECTRICITY, prod_water_elec.to("mmBtu/day"))
        energy_use_makeup.set_rate(EN_ELECTRICITY, makeup_water_elec.to("mmBtu/day"))

        # import/export
        import_product = field.import_export
        self.set_import_from_energy(energy_use_makeup)
        self.set_import_from_energy(energy_use_prod)
        import_product.set_import(self.name, WATER, makeup_water_mass + makeup_steam_mass)
        import_product.set_export(self.name, WATER, surface_disp_rate + subsurface_disp_rate)

        self.sum_intermediate_results()

    def get_water_treatment_elec(self, water_treatment_table, water_volume_rate):

        electricity = 0
        stages = sorted(water_treatment_table.index.unique())

        if self.num_stages > len(stages) or self.num_stages < 0:
            raise OpgeeException(
                f"water treatment: number of stages ({self.num_stages}) must be > 0 and <= {len(stages)}")

        for stage in stages[:self.num_stages]:
            stage_row = water_treatment_table.loc[stage]
            electricity_factor = (stage_row["Apply"].squeeze() *
                                  stage_row["EC"].squeeze()).sum()
            electricity += electricity_factor * water_volume_rate
            loss_factor = (stage_row["Apply"].squeeze() *
                           stage_row["Volume loss"].squeeze()).sum()
            water_volume_rate *= (1 - loss_factor)

        return electricity
