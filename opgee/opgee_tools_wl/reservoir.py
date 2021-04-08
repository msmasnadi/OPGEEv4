import numpy as np
import constant as const
import oil_flow_sheet as oil_flow
import gas_glow_sheet as gas_flow

def reservoir_well_interface(oil_tensor, water_tensor, gas_tensor, temp_pressure, added_stream):
    ###########################################################################################
    #################### Input Data Pre-processing ############################################
    ###########################################################################################
    liquid_phase = 0
    ############################## main rates ##################################################
    hydrocarbon_liquid_rate = np.sum(oil_tensor[:,liquid_phase])                      # tonne/day
    hydrocarbon_gas_rate = np.sum(oil_tensor[:,1])                                    # tonne/day
    water_rate = np.sum(water_tensor)                                                 # tonne/day
    gas_rate = np.sum(gas_tensor)                                                     # tonne/day
    
    ############################ temperature & pressure #########################################
    temperature = np.array(temp_pressure[0])                                          # F
    pressure = np.array(temp_pressure[1])                                             # psi

    ################################# addtional stream ##########################################
    stream_label = np.array(added_stream[:,0])                                        # number
    stream_switch = np.array(added_stream[:,1])                                       # true or false
    stream_tensor = np.array(added_stream[:,2])
    
    ############################ main rates + additional stream rate #############################
    # stream sum data initialization
    stream_hydrocarbon_liquid_rate = 0
    stream_hydrocarbon_gas_rate = 0
    stream_water_rate = 0
    stream_gas_rate = 0
    # stream sum data calculation
    for tensor in stream_tensor:
        stream_hydrocarbon_liquid_rate += np.sum(tensor[0][:,0])
        stream_hydrocarbon_gas_rate += np.sum(tensor[1][:,1])
        stream_water_rate += np.sum(tensor[2])
        stream_gas_rate += np.sum(tensor[3])
    total_hydrocarbon_liquid_rate   = hydrocarbon_liquid_rate + stream_hydrocarbon_liquid_rate  # tonne/day
    total_hydrocarbon_gas_rate      = hydrocarbon_gas_rate + stream_hydrocarbon_gas_rate        # tonne/day
    total_water_rate                = water_rate + stream_water_rate                            # tonne/day
    total_gas_rate                  = gas_rate + stream_gas_rate                                # tonne/day

    ###########################################################################################
    ################################## Calculation ############################################
    ###########################################################################################
    # reservoir_hydrocarbon_liquid_rate = 
print(oil_flow.gamma_o(19))

                    
