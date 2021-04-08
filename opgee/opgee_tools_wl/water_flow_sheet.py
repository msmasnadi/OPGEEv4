import constant as const
import Fuel_specs as fuel
import thermo_function as thermo_f
import gas_library as gas_lib
import numpy as np
################################# Water specific gravity ##################################
def GAMMA_W(W_TDS):
    # W_TDS is concentration of dissolved solids(TDS) in unit mg/L
    
    # see OPGEE v3.0a Flow Sheet tab row 83
    return 1 + W_TDS * 0.695 * 1e-6             