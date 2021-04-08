# import heavy_oil_upgrading as upgrading
import constant as const
import thermo_function as thermo_f
import oil_flow_sheet as oil_flow_f
import numpy as np
##################################################################################################################################
#################### Crude oil properties after refinery inlet gate######################################################################
##################################################################################################################################
# def Oil_API_at_refinery_inlet(API):
#     return input.API_grav                                              # API
# if ugrading.upgrader_type > 0:
#     Oil_API_at_refinery_inlet = upgrading.upgrading_data_table[0][ugrading.upgrader_type - 1]
# Oil_sg                                             = 141.5 / (131.5 + Oil_API_at_refinery_inlet)                 # fraction
# Oil_density_kg_per_bbl                             = const.liters_per_bbl * Oil_sg                               # kg/bbl
# Oil_density_lb_per_bbl                             = const.pounds_per_kilogram * Oil_density_kg_per_bbl          # lb/bbl


##################################################################################################################################
#################### Fluid properties at reservoir condition######################################################################
##################################################################################################################################
def GOR_bubblepoint(GOR):
    return GOR * 1.1618                                          # scf/bbl
################## bubble point pressure constants ###############################################################################
pbub_a1                                            = 5.527215                                                    # N/A
pbub_a2                                            = 0.783716                                                    # N/A
pbub_a3                                            = 1.841408                                                    # N/A
def p_bubblepoint(tempt, pressure, API, gas_comp, GOR):
    # temp is in F, pressure is in psia, API (check the upgrading)
    gas_SG = thermo_f.gas_sg(gas_comp)
    gamma_o = oil_flow_f.GAMMA_O(API)
    gor_bubble = GOR_bubblepoint(GOR)

    # see OPGEE v3.0a Fuel Specs tab M72
    first_part = gamma_o ** pbub_a1
    second_part = (gas_SG * gor_bubble * (tempt + 459.67)) ** pbub_a2
    third_part = np.exp(-pbub_a3 * gas_SG * gamma_o)
    return first_part * second_part * third_part

def GOR_res(tempt, pressure, API, gas_comp, GOR):
    # temp is in F, pressure is in psia, API (check the upgrading)
    gas_SG = thermo_f.gas_sg(gas_comp)
    gamma_o = oil_flow_f.GAMMA_O(API)

    # see OPGEE v3.0a Fuel Specs tab M80
    first_part = pressure ** (1 / pbub_a2) * gamma_o ** (-pbub_a1 /pbub_a2)
    second_part = np.exp(pbub_a3 / pbub_a2 * gas_SG* gamma_o)
    third_part = (459.67 + tempt) * gas_SG
    return np.min([first_part * second_part / third_part, GOR_bubblepoint(GOR)])
################### Bubblepoint oil formation volume factor #######################################################################
O_FVF_bub_a1                                       = 1                                                           # N/A
O_FVF_bub_a2                                       = 0.0000005253                                                # N/A
O_FVF_bub_a3                                       = 0.000181                                                    # N/A
O_FVF_bub_a4                                       = 0.000449                                                    # N/A
O_FVF_bub_a5                                       = 0.000206                                                    # N/A
def O_FVF_bub(tempt, pressure, API, gas_comp, GOR):
    # temp is in F, pressure is in psia, API (check the upgrading)
    gas_SG = thermo_f.gas_sg(gas_comp)
    gamma_o = oil_flow_f.GAMMA_O(API)
    gor_res = GOR_res(tempt, pressure, API, gas_comp, GOR)

    # see OPGEE v3.0a Fuel Specs tab M82
    first_part = O_FVF_bub_a1+O_FVF_bub_a2 * gor_res * (tempt- 60)
    second_part = O_FVF_bub_a3 * gor_res / gamma_o +O_FVF_bub_a4 * (tempt - 60) / gamma_o
    third_part = O_FVF_bub_a5 *gor_res * gas_SG / gamma_o
    return first_part + second_part + third_part

################### Isothermal compressibility correlation #######################################################################
Iso_comp_a1                                        = -0.000013668                                                # N/A
Iso_comp_a2                                        = -0.00000001925682                                           # N/A
Iso_comp_a3                                        = 0.02408026                                                  # N/A
Iso_comp_a4                                        = -0.0000000926091                                            # N/A

################### Heating value of crude oil ####################################################################################
O_LHV_a1                                           = 16796                                                       # N/A
O_LHV_a2                                           = 54.4                                                        # N/A
O_LHV_a3                                           = 0.217                                                       # N/A
O_LHV_a4                                           = 0.0019                                                      # N/A

O_HHV_a1                                           = 17672                                                       # N/A
O_HHV_a2                                           = 66.6                                                        # N/A
O_HHV_a3                                           = 0.316                                                       # N/A
O_HHV_a4                                           = 0.0014                                                      # N/A