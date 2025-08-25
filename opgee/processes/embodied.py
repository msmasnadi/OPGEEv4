"""
EmbodiedEmissions Process for OPGEE v4

Adds embodied CO2e associated with materials like steel/cement/mud and
infrastructure to the field's emissions. This is a thin wrapper around
the calculator functions in opgee.embodied.

NOTE: This module intentionally avoids tight coupling to OPGEE core to
reduce integration risk. The `run()` method demonstrates the pattern;
you may need to adapt calls to the current OPGEE API.
"""
from __future__ import annotations

from typing import Optional, Dict

from ..process import Process
from ..stream import Stream
from ..embodied.calc import EmbodiedComponent, sum_components
from ..embodied.library import LIBRARY
from pint import Quantity
from ..table_manager import TableManager
from ..table_update import TableUpdate
import math

# recognized materials in OPG embodied emission module
MAT_BARITE   = "barite"
MAT_CLAY     = "bentonite clay"
MAT_DRILL    = "diesel drilling fluid additive"
MAT_CEMENT   = "portland cement"
MAT_SAND     = "sand"
MAT_STEEL_LA = "steel, low alloy"
MAT_STEEL_UA = "steel, unalloyed"
MAT_IRON_ORE = "iron ore (hematite)"


class EmbodiedEmissions(Process):
    """
    Attributes / XML parameters (suggested):
      - include_embodied: bool (default True)
      - per_well_components: dict mapping material->kg for one well (or per year)
      - facility_components: dict mapping material->kg per field (or per year)
      - allocation: "per_energy" | "per_barrel" (default "per_energy")

    Behavior:
      - Sum embodied gCO2e across provided components.
      - If annualization or allocation is needed, scale to CI (gCO2e/MJ) using
        field annual energy output if accessible.
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        field = self.field
        self.include_embodied = field.attr("include_embodied")
        self.num_prod_wells = field.attr("num_prod_wells")
        self.num_water_inj_wells = field.attr("num_water_inj_wells")
        self.num_gas_inj_wells = field.attr("num_gas_inj_wells")
        self.field_depth = field.attr("depth")
        self.cache_attributes()

        self.table_mgr = TableManager()

    def cache_attributes(self):

        field = self.field

    def run(self, analysis) -> None:  # signature consistent with OPGEE Processes
        if not self.include_embodied:
            return

        # 1) Get total number of wells
        n_wells = self.num_prod_wells + self.num_water_inj_wells + self.num_gas_inj_wells

        # per well
        steel_map, total_steel_lbm = self.compute_casing_steel_mass_per_well()

        components = []
        if per_well:
            components.append(EmbodiedComponent("per_well", {k: v * max(n_wells, 0) for k, v in per_well.items()}))
        if facility:
            components.append(EmbodiedComponent("facility", facility))

        totals = sum_components(components)

        # 2) Try to allocate to CI if field energy output is available
        ci_g_per_mj = None
        try:
            # OPGEE typically tracks total energy exported as MJ/yr; adapt as needed:
            total_energy_MJ_per_year = None
            if hasattr(self, "field"):
                #total_energy_MJ_per_year = getattr(self.field, "total_energy_MJ_per_year", None)
                total_energy_MJ_per_year = Quantity(1000, "MJ/year")
                if total_energy_MJ_per_year is None and hasattr(self.field, "get_total_energy_MJ_per_year"):
                    total_energy_MJ_per_year = self.field.get_total_energy_MJ_per_year()

            if total_energy_MJ_per_year:
                ci_g_per_mj = totals.gco2e / total_energy_MJ_per_year
        except Exception:
            ci_g_per_mj = None

        # 3) Record results in a generic way so downstream reporting can pick it up.
        #    Replace with OPGEE-native emissions logging if available (e.g., self.save_process_data()).
        self.embodied_totals_gco2e = totals.gco2e
        self.embodied_totals_MJ = totals.mj
        self.embodied_ci_g_per_mj = ci_g_per_mj
        # If OPGEE's emissions interface is available, one might do something akin to:
        #   self.emissions.add_co2e(self.name, totals.gco2e)
        # or attach to a "non-operational" emissions category.

        return None

    def compute_casing_steel_mass_per_well(self):
        """
        Returns:
          (steel_per_len_by_component, total_steel_mass_lbm)

        steel_per_len_by_component: { 'Conductor 1': lbm/ft, ... }
        total_steel_mass_lbm: sum over components of (mass_per_ft * length_ft)

        Rules:
          - Use Moderate_casing_diam_in to look up mass/ft in steel_casing_mass_per_length.csv.
          - If diameter missing or not listed -> mass/ft = 0.0
          - Lengths are Moderate_length_ft, except:
              * 'Production casing' length = self.depth (ft) if available
              * 'Production tubing' length = self.depth (ft) if available
        """
        casing_df = self.table_mgr.get_table("casing_designs")
        steel_df = self.table_mgr.get_table("steel_casing_mass_per_length")

        steel_per_len_by_component: Dict[str, float] = {}
        total_steel_mass_lbm: float = 0.0

        # well depth, used for production casing/tubing
        depth_ft = self.field_depth

        for _, row in casing_df.iterrows():
            comp = row.name
            diam_in = row["Moderate_casing_diam_in"]
            mass_per_ft = self._nearest_mass_per_len(diam_in, steel_df)
            steel_per_len_by_component[comp] = mass_per_ft

            # pick length
            length_ft = Quantity(row["Moderate_length_ft"], "ft") or Quantity(0.0, "ft")
            if depth_ft is not None:
                if comp.lower() in ("production casing", "production tubing"):
                    length_ft = depth_ft

            total_steel_mass_lbm += mass_per_ft * length_ft

        return steel_per_len_by_component, total_steel_mass_lbm

    def _safe_float(x, default=None):
        try:
            v = float(x)
            if math.isnan(v):
                return default
            return v
        except Exception:
            return default

    def _nearest_mass_per_len(self, diam_in, steel_df) -> float:
        """Look up average lbm/ft by exact Outside_diam_in. Return 0.0 if not found."""
        if diam_in is None or math.isnan(diam_in):
            return Quantity(0.0, "lbm/ft")
        row = steel_df.loc[(steel_df.index.round(3) == round(diam_in, 3))]
        if not row.empty:
            return Quantity(row.iloc[0]["Mass_per_ft_avg_lbm"], "lbm/ft")
        return Quantity(0.0, "lbm/ft")

    def compute_cement_per_well(self):
