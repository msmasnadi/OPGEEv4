"""
Embodied materials library for OPGEE v4.

This module loads "selected values (SI)" for embodied emissions (gCO2e/kg)
and embodied energy (MJ/kg) for key materials from the Excel "Embodied Emissions"
sheet in OPGEE v3 (ported here as a CSV).

Sources:
- OPGEE v3 "Embodied Emissions" sheet (selected SI values).
- Brandt (2015), Embodied Energy and GHG Emissions from Material Use in
  Conventional and Unconventional Oil and Gas Operations. (used as conceptual basis).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Dict, Optional

@dataclass(frozen=True)
class MaterialIntensity:
    material: str
    gco2_per_kg: float
    mj_per_kg: float

def _default_csv_path() -> Path:
    # Look in a sibling "data" dir next to this package first; then next to this file.
    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent / "tables" / "embodied_materials.csv",
        here.parent / "embodied_materials.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    # Fall back to a path relative to current working dir
    return Path("tables/embodied_materials.csv")

def load_material_library(csv_path: Optional[Path] = None) -> Dict[str, MaterialIntensity]:
    """
    Load material intensities from a CSV with columns:
        material,gco2_per_kg,mj_per_kg
    Returns a dict keyed by lowercased material name.
    """
    if csv_path is None:
        csv_path = _default_csv_path()
    lib: Dict[str, MaterialIntensity] = {}
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["material"].strip()
            if not name:
                continue
            try:
                gco2 = float(row["gco2_per_kg"])
            except Exception:
                gco2 = float("nan")
            try:
                mj = float(row["mj_per_kg"])
            except Exception:
                mj = float("nan")
            lib[name.lower()] = MaterialIntensity(name, gco2, mj)
    return lib

# Eagerly load a default library when imported (safe to re-call load_material_library() later).
LIBRARY = load_material_library()
