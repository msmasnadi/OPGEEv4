import constant as const
import Fuel_specs as fuel
import thermo_function as thermo_f
import numpy as np
################################# Crude oil specific gravity ##################################
def GAMMA_O(API):
    temp = 131.5 + API
    return float(141.5 / temp)
################################# Solution gas oil ratio ######################################
def GOR_OS(tempt, pressure, API, gas_comp, GOR):
    # temp is in F, pressure is in psia
    pbub_a1 = fuel.pbub_a1
    pbub_a2 = fuel.pbub_a2
    pbub_a3 = fuel.pbub_a3
    gas_SG = thermo_f.gas_sg(gas_comp)
    GOR_bubble = fuel.GOR_bubblepoint(GOR)
    gamma_o = GAMMA_O(API)

    # see OPGEE v3.0a Flow Sheet tab row 33
    first_part = np.power(pressure, 1 / pbub_a2)
    second_part = np.power(gamma_o, -pbub_a1/pbub_a2)
    third_part = np.exp(pbub_a3 / pbub_a2 * gas_SG * gamma_o)
    forth_part = 1 / ((460 + tempt) * gas_SG)
    return np.min([first_part * second_part * third_part * forth_part, GOR_bubble]) #scf/bbl
################################# Saturated oil FVF #############################################
def FVF_SAT(tempt, pressure, API, gas_comp, GOR):
    # temp is in F, pressure is in psia
    gamma_o = GAMMA_O(API)
    gor_os = GOR_OS(tempt, pressure, API, gas_comp, GOR)
    gas_SG = thermo_f.gas_sg(gas_comp)
    
    # see OPGEE v3.0a Flow Sheet tab row 34
    first_part = 1 + 0.000000525 * gor_os * (tempt - 60)
    second_part = 0.000181 * gor_os / gamma_o + 0.000449 * (tempt - 60) /gamma_o
    third_part = 0.000206 * gor_os * gas_SG / gamma_o
    return first_part + second_part + third_part #bbl/STB
################################# Petroleum isothermal compressibility X #########################
def ISO_X(tempt, pressure, API, gas_comp, GOR):
    # temp is in F, pressure is in psia
    Iso_comp_a1 = fuel.Iso_comp_a1
    Iso_comp_a2 = fuel.Iso_comp_a2
    Iso_comp_a3 = fuel.Iso_comp_a3
    Iso_comp_a4 = fuel.Iso_comp_a4
    gor_os = GOR_OS(tempt, pressure, API, gas_comp, GOR)
    gas_SG = thermo_f.gas_sg(gas_comp)
    T_abs = tempt + 459.67                                                                  # R
                                                                   
    # see OPGEE v3.0a Flow Sheet tab row 35
    return Iso_comp_a1*gor_os+Iso_comp_a2*gor_os**2+Iso_comp_a3*gas_SG+Iso_comp_a4*T_abs**2 # N/A
################################# Petroleum isothermal compressibility c_o ########################
def ISO_CO(API):
    gamma_o = GAMMA_O(API)

    # see OPGEE v3.0a Flow Sheet tab row 36
    return (55.233 / 1000000)-(60.588 / 1000000) * gamma_o                                  # N/A
################################# Petroleum FVF undersaturated oil ################################
def FVF_UNSAT(tempt, pressure, API, gas_comp, GOR):
    # temp is in F, pressure is in psia
    O_FVF_bub = fuel.O_FVF_bub(tempt, pressure, API, gas_comp, GOR)
    p_bubblepoint = fuel.p_bubblepoint(tempt, pressure, API, gas_comp, GOR)

    # see OPGEE v3.0a Flow Sheet tab row 37
    return O_FVF_bub * np.exp(ISO_CO(API) * (p_bubblepoint-pressure))                       # bbl/STB
################################# Petroleum volume factor (FVF) ####################################
def OVF(tempt, pressure, API, gas_comp, GOR):
    p_bubblepoint = fuel.p_bubblepoint(tempt, pressure, API, gas_comp, GOR)
    if pressure < p_bubblepoint:
        return FVF_SAT(tempt, pressure, API, gas_comp, GOR)
    else:
        return FVF_UNSAT(tempt, pressure, API, gas_comp, GOR)                               # m3/std-m3
################################# Petroleum density ################################################
def RHO_O(tempt, pressure, API, gas_comp, GOR):
    # temp is in F, pressure is in psia
    gamma_o = GAMMA_O(API)
    gas_SG = thermo_f.gas_sg(gas_comp)
    gor_os = GOR_OS(tempt, pressure, API, gas_comp, GOR)
    ovf = OVF(tempt, pressure, API, gas_comp, GOR)

    # see OPGEE v3.0a Flow Sheet tab row 40
    rho_o_lb = (62.42796 * gamma_o + 0.0136 * gas_SG * gor_os) / ovf
    return  rho_o_lb * const.kilogram_per_pounds * const.ft3_per_m3 / 1000                    # tonne/m3
################################# Petroleum flow rate ################################################
def Q_O(oil_rate, tempt, pressure, API, gas_comp, GOR):
    # oil_rate is in tonne/day, temp is in F, pressure is in psia
    rho_o = RHO_O(tempt, pressure, API, gas_comp, GOR)
    
    # see OPGEE v3.0a Flow Sheet tab row 42
    return oil_rate / rho_o                                                                   # m3/day 
############################# Energy density crude oil (metric) ######################################
def LHV_O(API):
    LHV_O_btu = fuel.O_LHV_a1 + fuel.O_LHV_a2 * API - fuel.O_LHV_a3 * API**2 - fuel.O_LHV_a4 * API**3

    # see OPGEE v3.0a Flow Sheet tab row 44
    return LHV_O_btu * const.Joules_per_btu / const.kilogram_per_pounds / 1000000              # MJ/kg
############################# Energy flow rate LHV (metric) #########################################
def E_LHV_O(oil_rate, API):
    lhv_o = LHV_O(API)

    # see OPGEE v3.0a Flow Sheet tab row 47
    return lhv_o * oil_rate                                                                    # GJ/day
