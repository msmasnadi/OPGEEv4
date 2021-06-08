from ..process import Process
from ..log import getLogger

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
        output.copy_flow_rates_from(input)
        output.add_flow_rates_from(flooding_CO2)

        # bottom hole flowing pressure
        bottomhole_flowing_press = self.get_bottomhole_press(input)



    def impute(self):
        output = self.find_output_stream("crude oil")

        input = self.find_input_stream("crude oil")
        input.add_flow_rates_from(output)

    def get_bottomhole_press(self, input_stream):
        """

        :param input_stream: (stream) one combined stream from reservoir to reservoir well interface
        :return:(float) bottomhole pressure (BHP) (unit = psia)
        """
        field =self.get_field()
        oil = field.oil
        gas = field.gas

        # injection and production rate
        oil_prod_volume_rate = oil.volume_flow_rate(input_stream,
                                                    oil.oil_specific_gravity,
                                                    oil.gas_specific_gravity,
                                                    oil.gas_oil_ratio)
        # water_prod_volume_rate =
        pass

