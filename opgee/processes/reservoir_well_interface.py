#
# ReservoirWellInterface class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import numpy as np

from ..core import STP, TemperaturePressure
from ..log import getLogger
from ..process import Process
from ..stream import PHASE_GAS
from ..units import ureg

_logger = getLogger(__name__)  # data logging


class ReservoirWellInterface(Process):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self._required_inputs = [
            "oil",
        ]

        self._required_outputs = [
            "oil",
        ]

        self.frac_CO2_breakthrough = None
        self.num_prod_wells = None
        self.oil_volume_rate = None
        self.permeability = None
        self.productivity_index = None
        self.res_thickness = None
        self.res_tp = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field
        self.res_tp = TemperaturePressure(field.res_temp,
                                          field.res_press)
        self.num_prod_wells = field.num_prod_wells
        self.productivity_index = field.productivity_index
        self.permeability = self.attr("res_perm")
        self.res_thickness = self.attr("res_thickness")
        self.oil_volume_rate = field.oil_volume_rate
        self.frac_CO2_breakthrough = field.frac_CO2_breakthrough

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        # mass rate
        input = self.find_input_stream("oil")
        if input.is_uninitialized():
            return

        input.set_tp(self.res_tp)

        output = self.find_output_stream("oil")
        output.copy_flow_rates_from(input)

        CO2_flooding_rate = field.get_process_data("CO2_flooding_rate_init")
        if CO2_flooding_rate:
            CO2_breakthrough_mass_rate = CO2_flooding_rate * self.frac_CO2_breakthrough
            output.add_flow_rate("CO2", PHASE_GAS, CO2_breakthrough_mass_rate)

        # Check
        self.set_iteration_value(output.total_flow_rate())

        # bottom hole flowing pressure
        bottomhole_flowing_press = self.get_bottomhole_press(output)
        output.tp.set(T=self.res_tp.T, P=bottomhole_flowing_press)

    def impute(self):
        output = self.find_output_stream("oil")

        input = self.find_input_stream("oil")
        input.copy_flow_rates_from(output)

    def get_bottomhole_press(self, input_stream):
        """
        Get the bottomhole pressure (BHP)

        :param input_stream: (Stream) a combined stream with all flows from Reservoir
           to Reservoir-Well Interface

        :return:(pint.Quantity) bottomhole pressure (BHP) in units "psia"
        """
        oil = self.field.oil
        gas = self.field.gas
        water = self.field.water

        stream_temp = input_stream.tp.T.to("kelvin")
        res_press = input_stream.tp.P.to("psia")

        std_T = STP.T.to("kelvin")
        std_P = STP.P.to("Pa")

        # injection and production rate
        oil_prod_volume_rate = oil.volume_flow_rate(input_stream,
                                                    oil.oil_specific_gravity,
                                                    oil.gas_specific_gravity,
                                                    oil.gas_oil_ratio).to("bbl_oil/day")  # bbl/day
        water_prod_volume_rate = water.volume_flow_rate(input_stream).to("bbl_water/day")  # bbl/day
        gas_prod_volume_rate = gas.volume_flow_rate(input_stream).to("ft**3/day")
        fluid_rate_per_well = (oil_prod_volume_rate + water_prod_volume_rate) / self.num_prod_wells
        gas_rate_per_well = gas_prod_volume_rate / self.num_prod_wells

        # fluid properties at reservoir condition
        z_factor = gas.Z_factor(gas.reduced_temperature(input_stream), gas.reduced_pressure(input_stream))
        gas_viscosity = gas.viscosity(input_stream)  # cP
        gas_formation_volume_factor = gas.volume_factor(input_stream)

        # reservoir and flowing pressures at wellbore interface
        prod_liquid_flowing_BHP = max((input_stream.tp.P - fluid_rate_per_well / self.productivity_index).to("psia"),
                                      ureg.Quantity(100, "psia"))

        boundary = ureg.Quantity(2000., "psia")
        if res_press <= boundary:
            # flowing bottomhole pressure at producer (gas phase, low pressure)
            delta_P_square = (gas_viscosity * z_factor * std_P * stream_temp *
                              np.log(1000 / 0.5) * gas_rate_per_well /
                              (np.pi * self.permeability * self.res_thickness * std_T)).to("psia**2")
            delta = res_press ** 2 - delta_P_square
            prod_gas_flowing_BHP = np.sqrt(delta) if delta > 0.0 else STP.P
        else:
            delta_P_high = (gas_viscosity * gas_formation_volume_factor * np.log(1000 / 0.5) * gas_rate_per_well /
                            (2 * np.pi * self.permeability * self.res_thickness)).to("psia")
            prod_gas_flowing_BHP = res_press - delta_P_high

        prod_flowing_BHP = max(min(prod_liquid_flowing_BHP, prod_gas_flowing_BHP), STP.P)

        return prod_flowing_BHP
