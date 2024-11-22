#
# GasGathering class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import math
from .. import ureg
from ..emissions import EM_FUGITIVES
from ..log import getLogger
from ..process import Process
from ..stream import Stream

_logger = getLogger(__name__)


class GasGathering(Process):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        # TODO: avoid process names in contents.
        self._required_inputs = [
            "gas"
        ]

        self._required_outputs = [
            ("gas for gas dehydration",
             "gas for gas partition")
        ]

        self.site_fugitive_breakdown = self.model.site_fugitive_processing_unit_breakdown

        self.site_fugitive_intercept = None
        self.site_fugitive_slope = None
        self.processing_plant_average_site_throughput = None
        self.gathering_site_average_site_throughput = None

        self.cache_attributes()

    def cache_attributes(self):
        self.site_fugitive_intercept = self.attr("site_fugitive_intercept")
        self.site_fugitive_slope = self.attr("site_fugitive_slope")
        self.processing_plant_average_site_throughput = self.attr("processing_plant_average_site_throughput")
        self.gathering_site_average_site_throughput = self.attr("gathering_site_average_site_throughput")

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        if not self.all_streams_ready("gas"):
            return

        # mass_rate
        input = self.find_input_streams("gas", combine=True)
        if input.is_uninitialized():
            return

        input_stream_STP = Stream("input_stream_STP", tp=field.stp)
        input_stream_STP.copy_flow_rates_from(input, tp=field.stp)
        loss_rate = self.calculate_site_fugitive_loss_rate(input_stream_STP, self.gathering_site_average_site_throughput)
        gas_fugitives = self.set_gas_fugitives(input, loss_rate)

        output_gas = self.find_output_stream("gas for gas dehydration", raiseError=False)
        if output_gas is None:
            output_gas = self.find_output_stream("gas for gas partition")
        output_gas.copy_flow_rates_from(input)
        output_gas.subtract_rates_from(gas_fugitives)

        self.set_iteration_value(output_gas.total_flow_rate())

        # Calculate site fugitive loss rate for processing unit breakdown
        processing_unit_loss_rate_df =\
            self.site_fugitive_breakdown * \
            self.calculate_site_fugitive_loss_rate(input_stream_STP, self.processing_plant_average_site_throughput).m
        field.save_process_data(processing_unit_loss_rate_df=processing_unit_loss_rate_df)

        # emissions
        emissions = self.emissions
        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)

    def calculate_site_fugitive_loss_rate(self, input_stream, site_throughput):

        input_mass_rate = input_stream.total_flow_rate()
        input_volume_rate = self.field.gas.volume_flow_rate(input_stream)
        num_of_sites = input_volume_rate / site_throughput
        mass_rate_per_site = (input_mass_rate / num_of_sites).to("tonne/hr").m
        mass_rate_per_site = math.log10(mass_rate_per_site)
        loss_rate = \
            ureg.Quantity(10 ** (self.site_fugitive_intercept.to("frac").m + self.site_fugitive_slope.to(
                "frac").m * mass_rate_per_site), "frac")

        return loss_rate



