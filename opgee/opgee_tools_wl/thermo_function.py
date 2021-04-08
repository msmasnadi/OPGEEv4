import gas_library as gas_lib
import numpy as np
import constant as const
def gas_sg(gas_comp):                           # gas_comp is the gas input table with dimension of row * 2 (first col is gas tag) 
    size = gas_comp.shape
    row = size[0]
    gas_SG = 0
    for i in range(row):
        if float(gas_comp[i][1]) > 0:
            mw = gas_lib.dict_gas_pyromat[gas_comp[i][0]].mw()  # g/mol
            density = const.moles_of_gas_per_SCF_STP * mw
            # print(density)
            gas_SG = gas_SG + density * float(gas_comp[i][1])
    return gas_SG / gas_lib.dict_gas_pyromat["Air"].mw()



