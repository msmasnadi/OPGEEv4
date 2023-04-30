#
# Flaring class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..emissions import EM_FLARING
from ..log import getLogger
from ..process import Process
from ..stream import Stream

_logger = getLogger(__name__)


class Flaring(Process):

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        gas_to_flare = self.find_input_streams("gas for flaring", combine=True)  # type: Stream
        methane_slip = self.find_input_stream("methane slip")  # type: Stream
        if gas_to_flare.is_uninitialized() or methane_slip.is_uninitialized():
            return

        # emissions
        emissions = self.emissions
        sum_streams = Stream("combusted_stream", tp=gas_to_flare.tp)
        sum_streams.add_combustion_CO2_from(gas_to_flare)
        sum_streams.add_flow_rates_from(methane_slip)
        emissions.set_from_stream(EM_FLARING, sum_streams)
