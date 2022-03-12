#
# Immutable physical constants
#
from . import ureg

air_density_ratio          = ureg.Quantity(0.0749, "lb/ft**3")
air_elevation_corr         = ureg.Quantity(0.24, "btu/(lb*delta_degF)")
gravitational_acceleration = ureg.Quantity(9.8, "m/second**2")
gravitational_constant	   = ureg.Quantity(32.2, "(lb*ft)/(lbf*s**2)")
mol_per_scf	               = ureg.Quantity(1.1953, "mol/scf")
std_temperature            = ureg.Quantity(60.0, "degF")        # STP is defined in core.py
std_pressure               = ureg.Quantity(14.676, "psia")
tonne_to_bbl               = ureg.Quantity(7.33, "bbl_oil/tonne")
universal_gas_constant     = ureg.Quantity(8.314462618, "joule/mol/kelvin")
year_to_day                = ureg.Quantity(365., "day/year")
