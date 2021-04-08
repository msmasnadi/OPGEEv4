import constant as const
import Fuel_specs as fuel
import thermo_function as thermo_f
import gas_library as gas_lib
import numpy as np
################################# Gas total molar flow ##################################
def TOTMOLGAS(gas_rate):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    name = 0
    val = 1
    gas_molar_rate = 0.0

    # see OPGEE v3.0a Flow Sheet tab row 48
    for i in range(len(gas_rate)):
        temp = float(gas_rate[i][val]) / float(gas_lib.dict_gas_pyromat[gas_rate[i][name]].mw()) * const.grams_per_tonne
        # print(gas_rate[i][val])
        # print(gas_lib.dict_gas_pyromat[gas_rate[i][name]].mw())
        gas_molar_rate += temp

    return gas_molar_rate                                                                   # mol frac
################################# gas molar fraction ######################################
def Mol_frac(gas_rate):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    name = 0
    val = 1
    gas_molar_rate = TOTMOLGAS(gas_rate)
    # mol_frac is a dict, key is name tag, value is gas mol frac
    mol_frac = {}

    # see OPGEE v3.0a Flow Sheet tab row 33
    for i in range(len(gas_rate)):
        single_gas_molar_frac = float(gas_rate[i][val]) / float(gas_lib.dict_gas_pyromat[gas_rate[i][name]].mw()) * const.grams_per_tonne
        single_gas_molar_frac = single_gas_molar_frac / gas_molar_rate
        pair = []
        pair.append(gas_rate[i][name])
        pair.append(single_gas_molar_frac)
        mol_frac[pair[0]] = pair[1]
    return mol_frac                                                                         # dict of mol frac
################################# Gas specific gravity #############################################
def GAMMA_G(gas_rate):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    mol_frac = Mol_frac(gas_rate)
    name = 0
    val = 1
    gamma_g = 0
    for i in range(len(gas_rate)):
        temp = mol_frac[gas_rate[i][name]] * float(gas_lib.dict_gas_pyromat[gas_rate[i][name]].mw()) 
        gamma_g += temp
    
    # see OPGEE v3.0a Flow Sheet tab row 61
    return gamma_g / float(gas_lib.dict_gas_pyromat["Air"].mw())
################################# Ratio of specific heats #########################################
def CpCvRatio(gas_rate):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    name = 0
    val = 1
    cp = 0
    cv = 0
    for i in range(len(gas_rate)):
        cp += float(gas_rate[i][val]) * float(gas_lib.dict_gas_pyromat[gas_rate[i][name]].cp()) * 1000
        cv += float(gas_rate[i][val]) * float(gas_lib.dict_gas_pyromat[gas_rate[i][name]].cv()) * 1000
                                                                   
    # see OPGEE v3.0a Flow Sheet tab row 63
    if cv != 0:
        return cp / cv
    return "Error: cv = 0"
################################# Pseudocritical temperature (uncorrected) ########################
def T_PC(gas_rate):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    mol_frac = Mol_frac(gas_rate)
    first_term = 0
    # print(mol_frac)
    for name in mol_frac:
        frac = mol_frac[name]
        critical_temp_Rankine = float(gas_lib.dict_gas_tmo[name].Tc * const.Kelvin_to_Rankine)
        critical_pressure_psi = float(gas_lib.dict_gas_tmo[name].Pc * const.Pa_to_PSI)
        constantK = critical_temp_Rankine / critical_pressure_psi ** 0.5
        first_term += frac * constantK
    first_term = first_term **2
    
    second_term = 0
    third_term = 0
    for name in mol_frac:
        frac = mol_frac[name]
        critical_temp_Rankine = float(gas_lib.dict_gas_tmo[name].Tc * const.Kelvin_to_Rankine)
        critical_pressure_psi = float(gas_lib.dict_gas_tmo[name].Pc * const.Pa_to_PSI)
        T_pc_term1 = critical_temp_Rankine / critical_pressure_psi
        T_pc_term2 = T_pc_term1 **0.5
        second_term += frac * T_pc_term1 * 1/3
        third_term += frac * T_pc_term2
    third_term = third_term**2 * 2/3

    # see OPGEE v3.0a Flow Sheet tab row 64
    return first_term / (second_term + third_term)                                          # R
################################# Pseudocritical temperature (corrected) ################################
def T_PCC(gas_rate):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    mol_frac = Mol_frac(gas_rate)
    t_pc = T_PC(gas_rate)
    mol_perc_O2 = 0
    mol_perc_H2S = 0

    if "CO2" in mol_frac:
        mol_perc_O2 = mol_frac["CO2"]

    if "H2S" in mol_frac:
        mol_perc_H2S = mol_frac["H2S"]

    # see OPGEE v3.0a Flow Sheet tab row 65
    return t_pc-120*((mol_perc_O2+mol_perc_H2S)**0.9 - (mol_perc_O2+mol_perc_H2S)**1.6) + 15*(mol_perc_H2S**0.5 - mol_perc_H2S**4) # R
################################# Pseudocritical pressure (uncorrected) ####################################
def P_PC(gas_rate):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    mol_frac = Mol_frac(gas_rate)
    first_term = 0
    for name in mol_frac:
        frac = mol_frac[name]
        critical_temp_Rankine = float(gas_lib.dict_gas_tmo[name].Tc * const.Kelvin_to_Rankine)
        critical_pressure_psi = float(gas_lib.dict_gas_tmo[name].Pc * const.Pa_to_PSI)
        constantK = critical_temp_Rankine / critical_pressure_psi ** 0.5
        first_term += frac * constantK
    first_term = first_term **2
    
    second_term = 0
    third_term = 0
    for name in mol_frac:
        frac = mol_frac[name]
        critical_temp_Rankine = float(gas_lib.dict_gas_tmo[name].Tc * const.Kelvin_to_Rankine)
        critical_pressure_psi = float(gas_lib.dict_gas_tmo[name].Pc * const.Pa_to_PSI)
        T_pc_term1 = critical_temp_Rankine / critical_pressure_psi
        T_pc_term2 = T_pc_term1 **0.5
        second_term += frac * T_pc_term1 * 1/3
        third_term += frac * T_pc_term2
    third_term = third_term**2 * 2/3

    # see OPGEE v3.0a Flow Sheet tab row 64
    return first_term / (second_term + third_term)**2                                               # psia
################################# Pseudocritical pressure (corrected) ##############################
def P_PCC(gas_rate):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    mol_frac = Mol_frac(gas_rate)
    t_pc = T_PC(gas_rate)                                                                           # R
    t_pcc = T_PCC(gas_rate)                                                                         # R
    p_pc = P_PC(gas_rate)                                                                           # psia
    mol_perc_H2S = 0

    if "H2S" in mol_frac:
        mol_perc_H2S = mol_frac["H2S"]

    # see OPGEE v3.0a Flow Sheet tab row 67
    return (p_pc * t_pcc) / (t_pc - mol_perc_H2S * (1 - mol_perc_H2S) * (t_pc - t_pcc))             # psia
################################# Reduced temperature ################################################
def T_R(gas_rate, tempt):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    # tempt is in F
    tempt_abs = tempt + 459.67                                                                  # R
    # tempt_abs is abt tempt
    t_pcc = T_PCC(gas_rate)                                                                     # R
    
    # see OPGEE v3.0a Flow Sheet tab row 68
    return tempt_abs / t_pcc                                                                   # fraction 
############################# Reduced pressure #######################################################
def P_R(gas_rate, pressure):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    # pressure is in psia (abs)
    p_pcc = P_PCC(gas_rate)                                                                     # psia

    # see OPGEE v3.0a Flow Sheet tab row 69
    return pressure / p_pcc                                                                     # fraction
############################# Z-factor ##############################################################
def Z_factor(gas_rate, tempt, pressure):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    # tempt is in F
    # pressure is in psia (abs)
    t_r = T_R(gas_rate, tempt)
    p_r = P_R(gas_rate, pressure)
    z_factor_parameter = np.zeros(4) # initialization z_factor_parameter contains a list of z_factor from A,B,C,D

    # see OPGEE v3.0a Flow Sheet tab row 70 to row 74
    z_factor_parameter[0] = 1.39 * (t_r - 0.92) ** 0.5 - 0.36 *t_r - 0.101
    z_factor_parameter[1] = p_r * (0.62 - 0.23 * t_r) + p_r ** 2 * (0.066 / (t_r - 0.86) - 0.037) + 0.32 * t_r ** 6 / (10 ** (9 * t_r - 9))
                            # AD69* ( 0.62 - 0.23*AD68) + AD69^ 2 * (0.066 / (AD68 - 0.86) - 0.037) + 0.32 *AD68 ^ 6 / (10 ^ (9 *AD68 - 9))
    z_factor_parameter[2] = 0.132 - 0.32 * np.log10(t_r)
    z_factor_parameter[3] = 10 ** (0.3106 - 0.49 * t_r + 0.1824 * t_r ** 2)
    z_factor = (z_factor_parameter[0] + (1 - z_factor_parameter[0]) * np.exp(-1 * z_factor_parameter[1]) + z_factor_parameter[2] * p_r ** z_factor_parameter[3])
    return max(float(z_factor), 0.05)                                                                   # N/A
############################# Gas volume factor ###########################################################
def GVF(gas_rate, tempt, pressure):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    # tempt is in F
    # pressure is in psia (abs)
    z_factor = Z_factor(gas_rate, tempt, pressure)
    tempt_abs = tempt + 459.67                                                                          # R

    # see OPGEE v3.0a Flow Sheet tab row 75
    return const.Amb_press * z_factor * tempt_abs / (pressure * (const.Amb_temp + 459.67))              # m3/std-m3
############################# Gas density ################################################################
def RHO_G(gas_rate, tempt, pressure):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    # tempt is in F
    # pressure is in psia (abs)
    gvf = GVF(gas_rate, tempt, pressure)                                                                # m3/std-m3
    gamma_g = GAMMA_G(gas_rate)                                                                         # N/A

    # see OPGEE v3.0a Flow Sheet tab row 76
    return const.rho_air_stp * gamma_g / gvf                                                            # tonne/m3
############################# Gas mol weight ################################################################
def MW_G(gas_rate):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    gamma_g = GAMMA_G(gas_rate)

    # see OPGEE v3.0a Flow Sheet tab row 77
    return gamma_g * float(gas_lib.dict_gas_pyromat["Air"].mw())                                        # g/mol
############################# Gas flowrate ################################################################
def Q_G(gas_rate, tempt, pressure):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    # tempt is in F
    # pressure is in psia (abs)
    rho_g = RHO_G(gas_rate, tempt, pressure)                                                            # tonne/m3
    M_TOTGAS = 0
    val = 1
    for i in range(len(gas_rate)):
        M_TOTGAS += float(gas_rate[i][val])
    
    # see OPGEE v3.0a Flow Sheet tab row 78
    return M_TOTGAS / rho_g
############################# Energy density gas(metric) ############################################################
def LHV_G_met(gas_rate):
    # gas_rate is in tonne/day, the first colm is name tag, the second colm is rate
    LHV_G_tot = 0
    M_TOTGAS = 0
    for name, value in gas_rate:
        value = float(value)
        MW = gas_lib.dict_gas_tmo[name].MW # g/mol
        LHV_J_per_mol = -gas_lib.dict_gas_tmo[name].LHV #
        LHV_MJ_per_kg = LHV_J_per_mol / MW / 1000
        LHV_G_tot += value * LHV_MJ_per_kg
        M_TOTGAS += value
    
    # see OPGEE v3.0a Flow Sheet tab row 79
    return LHV_G_tot / M_TOTGAS                                                                             # MJ/kg
############################# Energy density gas ############################################################
def LHV_G(gas_rate):
    lhv_g_met = LHV_G_met(gas_rate)

    # see OPGEE v3.0a Flow Sheet tab row 78
    return lhv_g_met * const.btu_per_MJ / const.pounds_per_kilogram                                         # Btu/lb
############################# Energy density per SCF #######################################################
def LHV_G_scf(gas_rate):
    mol_frac = Mol_frac(gas_rate)
    LHV_G_tot = 0
    for name in mol_frac:
        frac = mol_frac[name]
        LHV_J_per_mol = -gas_lib.dict_gas_tmo[name].LHV
        LHV_Btu_per_mol = LHV_J_per_mol * const.btu_per_Joule
        LHV_Btu_per_scf = LHV_Btu_per_mol * const.moles_of_gas_per_SCF_STP
        LHV_G_tot += frac * LHV_Btu_per_scf

    # see OPGEE v3.0a Flow Sheet tab row 80
    return LHV_G_tot                                                                                         # Btu/scf
############################# Energy flow rate ##############################################################
def F_LHV_G(gas_rate):
    lhv_g_met = LHV_G_met(gas_rate)
    M_TOTGAS = 0
    for i in range(len(gas_rate)):
        M_TOTGAS += float(gas_rate[i][1])

    # see OPGEE v3.0a Flow Sheet tab row 81
    return M_TOTGAS * 1000 * lhv_g_met / 1055.05                                                               # mmBtu/d
