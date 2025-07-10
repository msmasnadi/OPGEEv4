#
# Gas Node class
#
# Author: Spencer Zhang
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)

class GasNode(Process):

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self._required_inputs = ["gas"]

        self._required_outputs = ["gas"]

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        input = self.find_input_stream("gas")

        output = self.find_output_stream("gas")
        output.copy_flow_rates_from(input, tp=field.wellhead_tp)
