import pyromat as py
import thermosteam as tmo
#######################################################################################################################################
############################################ Build gas thermodynamic library using pyromat ############################################
#######################################################################################################################################

############################################ import gas properties from pyromat #######################################################
CH4                 = py.get('ig.CH4')
N2                  = py.get('ig.N2')
O2                  = py.get('ig.O2')
CO2                 = py.get('ig.CO2')
H2O                 = py.get('ig.H2O')
C2H6                = py.get('ig.C2H6')
C3H8                = py.get('ig.C3H8')
C4H10               = py.get('ig.C4H10')
CO                  = py.get('ig.CO')
H2                  = py.get('ig.H2')
H2S                 = py.get('ig.H2S')
SO2                 = py.get('ig.SO2')
Air                 = py.get('ig.air')
########################################### Build gas properties label #################################################################
dict_gas_pyromat = {}
gas_label = ["N2", "O2", "CO2", "H2O", "CH4", "C2H6", "C3H8", "C4H10", "CO2", "H2", "H2S", "SO2", "Air"]
gas_thermo = [N2, O2, CO2, H2O, CH4, C2H6, C3H8, C4H10, CO2, H2, H2S, SO2, Air]
for i in range(len(gas_label)):
    dict_gas_pyromat[gas_label[i]] =  gas_thermo[i]

#######################################################################################################################################
############################################ Build gas thermodynamic library using thermosteam ############################################
#######################################################################################################################################

############################################ import gas properties from thermosteam #######################################################
CH4                 = tmo.Chemical('CH4')
N2                  = tmo.Chemical('N2')
O2                  = tmo.Chemical('O2')
CO2                 = tmo.Chemical('CO2')
H2O                 = tmo.Chemical('H2O')
C2H6                = tmo.Chemical('Ethane')
C3H8                = tmo.Chemical('Propane')
C4H10               = tmo.Chemical('Butane')
CO                  = tmo.Chemical('CO')
H2                  = tmo.Chemical('H2')
H2S                 = tmo.Chemical('H2S')
SO2                 = tmo.Chemical('SO2')
# Air                 = tmo.Chemical('N2')
########################################### Build gas properties label #################################################################
dict_gas_tmo = {}
gas_label = ["N2", "O2", "CO2", "H2O", "CH4", "C2H6", "C3H8", "C4H10", "CO2", "H2", "H2S", "SO2"]
gas_thermo = [N2, O2, CO2, H2O, CH4, C2H6, C3H8, C4H10, CO2, H2, H2S, SO2]
for i in range(len(gas_label)):
    dict_gas_tmo[gas_label[i]] =  gas_thermo[i]