"""
Embodied emissions calculator functions for OPGEE v4.

These functions compute embodied emissions (gCO2e) and embodied energy (MJ)
given material quantities (kg). The intent is to mirror/replace the Excel
"Embodied Emissions" worksheet logic in code, while keeping the API simple.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Tuple
import math

from .library import MaterialIntensity, LIBRARY

@dataclass
class EmbodiedComponent:
    """One component of embodied materials (e.g., steel casing, cement, mud)."""
    name: str
    materials_kg: Dict[str, float]  # material_name -> mass in kg

    def gco2e(self, lib: Dict[str, MaterialIntensity] = LIBRARY) -> float:
        total = 0.0
        for mat, mass in self.materials_kg.items():
            mi = lib.get(mat.lower())
            if mi is None or math.isnan(mi.gco2_per_kg):
                continue  # unknown material; caller can warn/log if desired
            total += mi.gco2_per_kg * mass
        return total

    def mj(self, lib: Dict[str, MaterialIntensity] = LIBRARY) -> float:
        total = 0.0
        for mat, mass in self.materials_kg.items():
            mi = lib.get(mat.lower())
            if mi is None or math.isnan(mi.mj_per_kg):
                continue
            total += mi.mj_per_kg * mass
        return total

@dataclass
class EmbodiedTotals:
    gco2e: float = 0.0
    mj: float = 0.0

    def add(self, other: "EmbodiedTotals") -> "EmbodiedTotals":
        self.gco2e += other.gco2e
        self.mj += other.mj
        return self

def sum_components(components: Iterable[EmbodiedComponent]) -> EmbodiedTotals:
    g = 0.0
    e = 0.0
    for c in components:
        g += c.gco2e()
        e += c.mj()
    return EmbodiedTotals(gco2e=g, mj=e)

# ----- Optional helpers for common oilfield items -----

def casing_mass_kg_from_weight_ft(total_weight_lb_per_ft: float, length_ft: float) -> float:
    """Compute casing steel mass from API "weight per foot" and length."""
    lb = total_weight_lb_per_ft * length_ft
    return lb * 0.45359237  # to kg

def cement_mass_kg_from_volume(volume_m3: float, density_kg_per_m3: float = 1900.0) -> float:
    """
    Estimate cement mass from slurry volume and density.
    Defaults to ~1900 kg/m^3; override per cement blend per OPGEE v2/v3 docs.
    """
    return volume_m3 * density_kg_per_m3

def mud_mass_kg_from_volume(volume_m3: float, density_kg_per_m3: float = 1400.0) -> float:
    """Rough estimate for drilling mud; override as needed."""
    return volume_m3 * density_kg_per_m3
