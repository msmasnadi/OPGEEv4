#
# LNGLiquefaction class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class LNGLiquefaction(Process):
    """
    LNG liquefaction calculate emission of produced gas to liquefaction
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self._required_inputs = [
            "LNG",
        ]

        self._required_outputs = [
            "gas",
            # "gas fugitives"       # TODO: future feature
        ]


        self.ancillary_loads = None
        self.compression_refrigeration_load = None
        self.NG_to_liq_rate = None

        self.cache_attributes()

    def cache_attributes(self):
        self.ancillary_loads = self.attr("ancillary_loads")
        self.compression_refrigeration_load = self.attr("compression_refrigeration_load")
        self.NG_to_liq_rate = self.attr("NG_to_liq_rate")

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("LNG")

        if input.is_uninitialized():
            return

        # TODO: delete unused code here and below
        # total_load = (self.compression_refrigeration_load + self.ancillary_loads) * self.NG_to_liq_rate

        gas_to_transport = self.find_output_stream("gas")
        gas_to_transport.copy_flow_rates_from(input)
        gas_to_transport.tp.set(T=self.field.LNG_temp)

        #TODO: Future versions of OPGEE may treat this process in more detail.

        # loss_rate = self.venting_fugitive_rate()
        # gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        # gas_fugitives = self.find_output_stream("gas fugitives")
        # gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)
        # gas_fugitives.set_temperature_and_pressure(self.std_temp, self.std_press)

