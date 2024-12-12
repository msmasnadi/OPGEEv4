#
# GasPartition class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..core import STP
from ..log import getLogger
from ..process import Process
from ..stream import PHASE_GAS, Stream

_logger = getLogger(__name__)


class VFPartition(Process):
    """
    VF (Venting and Flaring) partition is to check the reasonable amount of gas goes to venting, flaring and further process
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        # TODO: avoid process names in contents.
        self._required_inputs = [
            "gas for partition",
        ]

        self._required_outputs = [
            "gas for flaring",
            "methane slip",
            "gas for venting",
        ]

        self.mol_per_scf = self.field.model.const("mol-per-scf")

        self.FOR = None
        self.combusted_gas_frac = None
        self.oil_volume_rate = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field
        self.FOR = field.FOR
        self.oil_volume_rate = field.oil_volume_rate

        # TODO: add smart default to this parameter from lookup table
        self.combusted_gas_frac = field.attr("combusted_gas_frac")

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        if not self.all_streams_ready("gas for partition"):
            return

        input = self.find_input_streams("gas for partition", combine=True)
        if input.is_uninitialized():
            return

        input_stream_mol_fracs = field.gas.component_molar_fractions(input)
        SCO_bitumen_ratio = field.get_process_data("SCO_bitumen_ratio")
        temp = self.oil_volume_rate * self.FOR
        if SCO_bitumen_ratio:
            volume_of_gas_flared = temp / SCO_bitumen_ratio
        else:
            volume_of_gas_flared = temp

        temp = volume_of_gas_flared * input_stream_mol_fracs
        volume_rate_gas_combusted = temp * self.combusted_gas_frac
        volume_rate_gas_slip = temp * (1 - self.combusted_gas_frac)

        temp = field.gas.component_gas_rho_STP[volume_rate_gas_combusted.index]
        mass_rate_gas_combusted =\
            volume_rate_gas_combusted * temp
        mass_rate_gas_slip = volume_rate_gas_slip * temp

        gas_to_flare = self.find_output_stream("gas for flaring")
        gas_to_flare.set_rates_from_series(mass_rate_gas_combusted, PHASE_GAS, input)
        gas_to_flare.set_tp(tp=STP)

        methane_slip = self.find_output_stream("methane slip")
        temp = Stream("temp", tp=input.tp)
        temp.copy_flow_rates_from(input)
        methane_slip.set_rates_from_series(mass_rate_gas_slip, PHASE_GAS, temp.subtract_rates_from(gas_to_flare, PHASE_GAS))
        methane_slip.set_tp(tp=STP)

        output_gas = self.find_output_stream("gas for venting")
        output_gas.copy_flow_rates_from(input)
        output_gas.subtract_rates_from(gas_to_flare)
        output_gas.subtract_rates_from(methane_slip)

        self.set_iteration_value(output_gas.total_flow_rate())
