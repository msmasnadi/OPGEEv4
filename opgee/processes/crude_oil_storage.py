#
# CrudeOilStorage class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .. import ureg
from ..emissions import EM_FUGITIVES
from ..log import getLogger
from ..process import Process
from ..stream import PHASE_GAS
from ..stream import Stream

_logger = getLogger(__name__)


class CrudeOilStorage(Process):
    """
        A process that represents the storage of crude oil in a field.

        This process takes crude oil as an input and produces three output streams:
        - gas for partition: gas that is flared
        - gas for VRU: gas that is sent to a vapor recovery unit
        - oil: crude oil that is transported out of the storage facility

        The process calculates the mass rate of crude oil input, as well as the amount of gas that is exsolved upon flashing.
        It then calculates the rates of gas that are sent to the flare, vapor recovery unit, and fugitives, based on the
        exsolved gas and user-defined factors. Finally, it calculates the mass rate of crude oil that is transported out of
        the storage facility, and sets the output streams accordingly.

        This process does not use any energy, and only produces emissions from the gas fugitives stream.

        Attributes:
            field: The `Field` object that this process belongs to.
            oil: The `Oil` object representing the type of crude oil being stored.
            oil_sands_mine: A string representing the name of the oil sands mine, or "None" if there is no mine.
            API: The API gravity of the crude oil being stored.
            storage_gas_comp: The composition of the storage gas.
            CH4_comp: The methane component of the storage gas composition.
            f_FG_CS_VRU: The fraction of exsolved gas that is sent to the vapor recovery unit.
            f_FG_CS_FL: The fraction of exsolved gas that is flared.
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        # TODO: avoid process names in contents.
        self._required_inputs = [
            "oil for storage",
        ]

        self._required_outputs = [
            "gas for partition",
            "gas for VRU",
            "oil",
        ]

        self.CH4_comp = None
        self.f_FG_CS_FL = None
        self.f_FG_CS_VRU = None
        self.oil_sands_mine = None

        self.storage_gas_comp = self.field.imported_gas_comp["Storage Gas"]
        self.CH4_comp = self.storage_gas_comp["C1"]

        self.cache_attributes()

    def cache_attributes(self):
        self.oil_sands_mine = self.field.oil_sands_mine
        self.f_FG_CS_VRU = self.attr("f_FG_CS_VRU")
        self.f_FG_CS_FL = self.attr("f_FG_CS_FL")

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        # TODO: LPG to blend with crude oil need to be implement after gas branch
        # mass rate
        input_stream = self.find_input_streams("oil for storage", combine=True)
        if input_stream.is_uninitialized():
            return

        oil_mass_rate = input_stream.liquid_flow_rate("oil")

        # Calculate gas exsolved upon flashing
        loss_rate = field.component_fugitive_table[self.name]
        loss_rate = ureg.Quantity(loss_rate.m, "kg/bbl_oil")
        oil_volume_rate = oil_mass_rate / (field.oil.specific_gravity(input_stream.API) * field.water.density())
        gas_exsolved_upon_flashing = oil_volume_rate * loss_rate / self.CH4_comp \
            if self.oil_sands_mine == "None" else ureg.Quantity(0, "tonne/day")

        # Calculate vapor to flare, VRU, and gas fugitives
        temp = gas_exsolved_upon_flashing * self.storage_gas_comp
        vapor_to_flare = self.f_FG_CS_FL * temp
        vapor_to_VRU = self.f_FG_CS_VRU * temp
        gas_fugitives = (1 - self.f_FG_CS_VRU - self.f_FG_CS_FL) * gas_exsolved_upon_flashing * self.storage_gas_comp

        # Set output streams
        stp = field.stp
        output_flare = self.find_output_stream("gas for partition")
        output_flare.set_rates_from_series(vapor_to_flare, PHASE_GAS)
        output_flare.set_tp(stp)

        output_VRU = self.find_output_stream("gas for VRU")
        output_VRU.set_rates_from_series(vapor_to_VRU, PHASE_GAS)
        output_VRU.set_tp(stp)

        gas_fugitive_stream = Stream("gas_fugitives", tp=self.field.stp)
        gas_fugitive_stream.set_rates_from_series(gas_fugitives, PHASE_GAS)
        gas_fugitive_stream.set_tp(stp)

        output_transport = self.find_output_stream("oil")
        oil_to_transport_mass_rate = (oil_mass_rate -
                                      output_VRU.total_gas_rate() -
                                      output_flare.total_gas_rate() -
                                      gas_fugitive_stream.total_gas_rate())
        output_transport.set_liquid_flow_rate("oil", oil_to_transport_mass_rate, tp=stp)
        output_transport.set_API(input_stream.API)

        iteration_value =\
            output_flare.total_flow_rate() +\
            output_VRU.total_flow_rate() +\
            gas_fugitive_stream.total_flow_rate() +\
            output_transport.total_flow_rate()
        self.set_iteration_value(iteration_value)

        # No energy-use for storage

        # emissions
        emissions = self.emissions
        emissions.set_from_stream(EM_FUGITIVES, gas_fugitive_stream)
