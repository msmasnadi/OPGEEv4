#
# Venting class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .. import ureg
from ..emissions import EM_VENTING, EM_FUGITIVES
from ..log import getLogger
from ..process import Process
from ..stream import Stream

_logger = getLogger(__name__)


class Venting(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.VOR = field.attr("VOR")
        self.gas = field.gas
        self.pipe_leakage = field.attr("surface_piping_leakage")
        self.gas_lifting = field.attr("gas_lifting")
        self.GOR = field.attr("GOR")
        self.FOR = field.attr("FOR")
        self.WOR = field.attr("WOR")
        self.GLIR = field.attr("GLIR")
        self.oil_prod = field.attr("oil_prod")
        self.res_press = field.attr("res_press")
        self.water_prod = self.oil_prod * self.WOR
        self.VOR_over_GOR = self.VOR / (self.GOR - self.FOR) if (self.GOR.m - self.FOR.m) > 0 else ureg.Quantity(0,
                                                                                                                 "frac")
        self.imported_fuel_gas_comp = field.imported_gas_comp["Imported Fuel"]
        self.imported_fuel_gas_mass_fracs = field.gas.component_mass_fractions(self.imported_fuel_gas_comp)

        self.is_first_loop = True

    def run(self, analysis):
        self.print_running_msg()
        field = self.field
        # mass rate

        input = self.find_input_stream("gas for venting")  # type: Stream
        if input.is_uninitialized():
            return

        methane_to_venting = input.gas_flow_rate("C1") * self.VOR_over_GOR
        venting_frac = \
            methane_to_venting / input.gas_flow_rate("C1") \
                if input.gas_flow_rate("C1").m != 0 else ureg.Quantity(0, "frac")
        fugitive_frac = \
            self.pipe_leakage / input.gas_flow_rate("C1") \
                if input.gas_flow_rate("C1").m != 0 else ureg.Quantity(0, "frac")

        gas_to_vent = Stream("venting_gas", tp=field.stp)
        gas_to_vent.copy_flow_rates_from(input, tp=field.stp)
        gas_to_vent.multiply_flow_rates(venting_frac.to("frac").m)

        if self.is_first_loop:
            field.save_process_data(gas_to_vent_init=gas_to_vent)
            self.is_first_loop = False

        if self.gas_lifting and field.get_process_data("gas_to_vent_init"):
            gas_to_vent = field.get_process_data("gas_to_vent_init")

        gas_fugitives = self.set_gas_fugitives(input, fugitive_frac.to("frac").m)

        gas_to_gathering = self.find_output_stream("gas for gas gathering")
        gas_tp_after_separation = field.get_process_data("gas_tp_after_separation")
        gas_to_gathering.copy_flow_rates_from(input, tp=gas_tp_after_separation)
        gas_to_gathering.subtract_rates_from(gas_to_vent)
        gas_to_gathering.subtract_rates_from(gas_fugitives)

        self.set_iteration_value(gas_to_gathering.total_flow_rate())

        # emissions
        emissions = self.emissions
        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
        emissions.set_from_stream(EM_VENTING, gas_to_vent)
