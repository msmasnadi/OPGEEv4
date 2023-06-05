#
# Immutable physical constants
#
from pint import Quantity

air_density_ratio          = Quantity(0.0749, "lb/ft**3")
air_elevation_corr         = Quantity(0.24, "btu/(lb*delta_degF)")
gravitational_acceleration = Quantity(9.8, "m/second**2")
gravitational_constant	   = Quantity(32.2, "(lb*ft)/(lbf*s**2)")
mol_per_scf	               = Quantity(1.1953, "mol/scf")
std_temperature            = Quantity(60.0, "degF")        # STP is defined in core.py
std_pressure               = Quantity(14.676, "psia")
tonne_to_bbl               = Quantity(7.33, "bbl_oil/tonne")
universal_gas_constant     = Quantity(8.314462618, "joule/mol/kelvin")
year_to_day                = Quantity(365., "day/year")
petrocoke_LHV              = Quantity(26949429, "btu/tonne")
