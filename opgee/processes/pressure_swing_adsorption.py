#
# PressureSwingAdsorption class
#
# Author: Spencer Zhihao Zhang
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#

import numpy as np

from ..units import ureg
from ..emissions import EM_FUGITIVES, EM_VENTING, EM_H2
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY
from ..error import OpgeeException
from ..log import getLogger
from ..process import Process
from ..process import run_corr_eqns
from ..thermodynamics import ChemicalInfo
from .shared import get_bounded_value, predict_blower_energy_use
from ..stream import PHASE_GAS

_logger = getLogger(__name__)


class PressureSwingAdsorption(Process):
    """
        This class represents the gas dehydration process in an oil and gas field.
        It calculates the energy consumption and emissions related to the gas dehydration process.

        Attributes:
            gas_dehydration_tbl (DataFrame): A table containing gas dehydration correlations.
            mol_to_scf (float): Constant to convert moles to standard cubic feet.
            air_elevation_const (float): Constant used for air elevation correction.
            air_density_ratio (float): Constant used for air density ratio calculation.
            reflux_ratio (float): Reflux ratio used in the gas dehydration process.
            regeneration_feed_temp (float): Regeneration feed temperature used in the gas dehydration process.
            eta_reboiler_dehydrator (float): Efficiency of the reboiler in the dehydrator.
            air_cooler_delta_T (float): Temperature difference across the air cooler.
            air_cooler_press_drop (float): Pressure drop across the air cooler.
            air_cooler_fan_eff (float): Efficiency of the air cooler fan.
            air_cooler_speed_reducer_eff (float): Efficiency of the air cooler speed reducer.
            water_press (float): Pressure of the water in the process.
            gas_path (str): The path of the gas in the process.
            gas_path_dict (dict): Dictionary mapping gas path names to stream names.
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        # TODO: avoid process names in contents.
        self._required_inputs = [
            "gas",
        ]

        self._required_outputs = [
            "gas",
            #"iteration gas"
        ]

        model = self.field.model

        # get relevant parameters from attribute/input/model tables for later calculation
        self.gas_dehydration_tbl = model.gas_dehydration_tbl
        self.mol_to_scf = model.const("mol-per-scf")
        self.air_elevation_const = model.const("air-elevation-corr")
        self.air_density_ratio = model.const("air-density-ratio")

        self.air_cooler_delta_T = None
        self.air_cooler_fan_eff = None
        self.air_cooler_press_drop = None
        self.air_cooler_speed_reducer_eff = None
        self.eta_reboiler_dehydrator = None
        self.gas_path = None
        self.reflux_ratio = None
        self.regeneration_feed_temp = None
        self.water_press = None

        # save attribute values to self.xx
        self.cache_attributes()

    def cache_attributes(self):
        field = self.field

        self.flaring = self.attr("flaring")
        self.slip_rate = field.attr("slip_rate")
        self.gas_path = field.gas_path

    def run(self, analysis):

        self.print_running_msg()

        input = self.find_input_stream("gas")

        # separate stream into (1) pure H2 (2) waste gas
        output = self.find_output_stream("gas")

        H2_loss = input.gas_flow_rate("H2")*self.slip_rate
        H2_remain = input.gas_flow_rate("H2") - H2_loss

        output.copy_flow_rates_from(input)
        #output.set_gas_flow_rate("H2", H2_remain)

        #self.emissions.set_rate(EM_VENTING, EM_H2, H2_loss)
