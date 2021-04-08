#########################################################################################################
#################### Conversion Factor ##################################################################
#########################################################################################################

################################# Table 1.1: Length conversion factors ##################################
feet_per_meter	                = 3.2808                                                # ft/m
meters_per_foot	                = 1 / feet_per_meter                                    # m/ft
meters_per_inch	                = 0.0254                                                # m/in
inches_per_meter	            = 1 / meters_per_inch                                   # in/m
miles_per_kilometer	            = 0.62137                                               # mi/km

################################# Table 1.2: Mass conversion factors ####################################
pounds_per_kilogram	            = 2.204                                                 # lb/kg
kilogram_per_pounds	            = 0.45359237                                            # kg/lb
grams_per_kilogram	            = 1000                                                  # g/kg
grams_per_tonne                 = grams_per_kilogram * 1000                             # g/tonne
kilograms_per_gram	            = 1 / grams_per_kilogram                                # kg/g
grams_per_pound	                = kilogram_per_pounds * grams_per_kilogram              # g/lb
pounds_per_gram	                = 1 / grams_per_pound                                   # lb/g
pounds_per_component_day	    = kilogram_per_pounds * 1000 * 365.24                   # g per component-yr

################################# Table 1.3: Volume conversion factors ##################################
m3_per_yd3	                    = 1.308                                                 # m3/yd3
gallons_per_barrel	            = 42                                                    # gal/bbl
bbls_per_gallon	                = 1 / gallons_per_barrel                                # bbl/gal
liters_per_gallon	            = 3.78                                                  # l/gal
liters_per_cuft	                = 28.3168466                                            # l/cuft
liters_per_bbl	                = 158.9873                                              # l/bbl
m3_per_bbl	                    = liters_per_bbl / 1000                                 # m3/bbl
ft3_per_bbl	                    = m3_per_bbl * 35.3146667                               # ft3/bbl
bbl_per_m3	                    = 1 / m3_per_bbl                                        # bbl/m3
liters_of_gas_per_mol_STP	    = 22.4                                                  # l/mol
moles_of_gas_per_SCF_STP	    = 1.2023                                                # mol/scf
ft3_per_m3	                    = ft3_per_bbl / m3_per_bbl                               # ft3/m3

################################# Table 1.4: Energy conversion factors ##################################
btu_per_Joule	                = 0.00094781712                                         # btu/J
btu_per_MJ	                    = btu_per_Joule * 10**6                                 # btu/MJ 
Joules_per_btu	                = 1055.05                                               # J/btu
MJ_per_btu	                    = Joules_per_btu / 10**6                                # MJ/btu
MJ_per_mmbtu	                = Joules_per_btu                                        # MJ/mmbtu
Joules_per_calorie	            = 4.18                                                  # J/cal
MJ_per_kWh	                    = 3.6                                                   # MJ/kWh
kWh_per_MJ	                    = 1 / MJ_per_kWh                                        # kWh/MJ
kWh_per_btu	                    = MJ_per_btu * kWh_per_MJ                               # kWh/btu
btu_per_kWh	                    = 1 / kWh_per_btu                                       # btu/kWh
mmbtu_per_MWh	                = btu_per_kWh / 1000                                    # mmbtu/MWh
MJ_per_J                        = 1e+6                                                  # MJ/J
################################## Table 1.5 Temperature Converstion ###################################
Kelvin_to_Rankine               = 1.8                                                   # K/R


##################################Table 1.6 Pressure Conversion ########################################
Pa_to_PSI                       = 0.000145038                                           # Pa / psi
################################# Table 2.4: Composition of moist air ###################################
H2O_comp                        = 0.02                                                  # mols/ mol moist air
N2_comp                         = 0.774396                                              #

################################# Table 2.7: Ambient Condition ###################################
Amb_temp                        = 60                                                    # F
Amb_press                       = 14.676                                                # psia
rho_air_stp                     = 0.001225                                              # kg/m3

