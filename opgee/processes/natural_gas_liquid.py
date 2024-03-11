#
# NGL class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)

class NGL(Process):
    def run(self, analysis):
        self.print_running_msg()

        if not self.all_streams_ready("gas for NGL"):
            return

        input = self.find_input_streams("gas for NGL", combine=True)
        if input.is_uninitialized():
            return

        output = self.find_output_stream("LPG")
        output.copy_flow_rates_from(input)

