import numpy as np
from ..process import Process
from ..log import getLogger
from opgee import ureg

_logger = getLogger(__name__)  # data logging


class ReservoirWellInterface(Process):
    def run(self, analysis):
        self.print_running_msg()

        field = self.get_field()

        res_temp = field.attr("res_temp")
        res_press = field.attr("res_press")

        # mass rate
        input = self.find_input_stream("crude oil")
        input.set_temperature_and_pressure(res_temp, res_press)
        flooding_CO2 = self.find_input_stream("CO2")
        flooding_CO2.set_temperature_and_pressure(res_temp, res_press)

        output = self.find_output_stream("crude oil")
        # Check
        self.set_iteration_value(output.total_flow_rate())
        output.copy_flow_rates_from(input)
        output.add_flow_rates_from(flooding_CO2)

        # bottom hole flowing pressure
        bottomhole_flowing_press = self.get_bottomhole_press(input)
        output.set_temperature_and_pressure(res_temp, bottomhole_flowing_press)

    def impute(self):
        output = self.find_output_stream("crude oil")

        input = self.find_input_stream("crude oil")
        input.add_flow_rates_from(output)

    def get_bottomhole_press(self, input_stream):
        """

        :param input_stream: (stream) one combined stream from reservoir to reservoir well interface
        :return:(float) bottomhole pressure (BHP) (unit = psia)
        """
        field = self.get_field()
        oil = field.oil
        gas = field.gas
        water = field.water

        num_prod_wells = field.attr("num_prod_wells")
        productivity_index = field.attr("prod_index")
        permeability = field.attr("res_perm")
        thickness = field.attr("res_thickness")
        std_press = field.model.const("std-pressure").to("Pa")
        res_press = input_stream.pressure.to("psia")
        std_temp = field.model.const("std-temperature").to("kelvin")
        stream_temp = input_stream.temperature.to("kelvin")

        # injection and production rate
        oil_prod_volume_rate = oil.volume_flow_rate(input_stream,
                                                    oil.oil_specific_gravity,
                                                    oil.gas_specific_gravity,
                                                    oil.gas_oil_ratio).to("bbl_oil/day")  # bbl/day
        water_prod_volume_rate = water.volume_flow_rate(input_stream).to("bbl_water/day")  # bbl/day
        gas_prod_volume_rate = gas.volume_flow_rate(input_stream).to("ft**3/day")
        fluid_rate_per_well = (oil_prod_volume_rate + water_prod_volume_rate) / num_prod_wells
        gas_rate_per_well = gas_prod_volume_rate / num_prod_wells

        # fluid properties at reservoir condition
        z_factor = gas.Z_factor(gas.reduced_temperature(input_stream), gas.reduced_pressure(input_stream))
        gas_viscosity = gas.viscosity(input_stream)            # cP
        gas_formation_volume_factor = gas.volume_factor(input_stream)

        # reservoir and flowing pressures at wellbore interface
        prod_liquid_flowing_BHP = (input_stream.pressure - fluid_rate_per_well / productivity_index).to("psia")

        boundary = ureg.Quantity(2000, "psia")
        if res_press <= boundary:
            # flowing bottomhole pressure at producer (gas phase, low pressure)
            delta_P_square = (gas_viscosity * z_factor * std_press * stream_temp * np.log(1000/0.5) * gas_rate_per_well /
                              (np.pi * permeability * thickness * std_temp)).to("psia**2")
            prod_gas_flowing_BHP = np.sqrt(res_press**2 - delta_P_square)
        else:
            # flowing bottomhole pressure at producer (gas phase, high pressure)
            delta_P_high = (gas_viscosity * gas_formation_volume_factor * np.log(1000/0.5) * gas_rate_per_well /
                            (2 * np.pi * permeability * thickness)).to("psia")
            prod_gas_flowing_BHP = res_press - delta_P_high

        prod_flowing_BHP = min(prod_liquid_flowing_BHP, prod_gas_flowing_BHP)
        return prod_flowing_BHP






