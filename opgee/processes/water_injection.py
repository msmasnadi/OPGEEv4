#
# WaterInjection class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
# WaterInjection class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import numpy as np

from .shared import get_energy_carrier, get_energy_consumption
from ..emissions import EM_COMBUSTION
from ..error import OpgeeException
from ..log import getLogger
from ..process import Process
from .. import ureg

_logger = getLogger(__name__)


class WaterInjection(Process):
    """
        TBD

        input streams:
            -

        output streams:
            -
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.gravitation_acc = self.model.const("gravitational-acceleration")
        self.gravitation_const = self.model.const("gravitational-constant")
        self.water_density = self.water.density()

        self.depth = None
        self.eta_pump = None
        self.friction_factor = None
        self.num_water_inj_wells = None
        self.press_pump = None
        self.prime_mover_type = None
        self.prod_tubing_diam = None
        self.productivity_index = None
        self.res_press = None
        self.water_flooding = None
        self.water_reinjection = None
        self.xsection_area = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field
        self.water_reinjection = field.water_reinjection
        self.water_flooding = field.water_flooding
        self.productivity_index = field.productivity_index
        self.res_press = field.res_press
        self.num_water_inj_wells = field.num_water_inj_wells

        self.depth = field.depth
        self.prod_tubing_diam = field.prod_tubing_diam
        self.xsection_area = np.pi * (self.prod_tubing_diam / 2) ** 2
        self.friction_factor = field.friction_factor
        self.press_pump = self.attr("press_pump")
        self.eta_pump = self.attr("eta_pump")
        self.prime_mover_type = self.attr("prime_mover_type")

    def check_enabled(self):
        if not self.water_reinjection and not self.water_flooding:
            self.set_enabled(False)

    def run(self, analysis):
        self.print_running_msg()

        if self.num_water_inj_wells.m == 0:
            raise OpgeeException(f"Got zero number of injector in the {self.name} process")

        input = self.find_input_stream("water for water injection")
        if input.is_uninitialized():
            return

        water_mass = input.liquid_flow_rate("H2O")
        water_volume = water_mass / self.water_density
        single_well_water_volume = water_volume / self.num_water_inj_wells

        wellbore_flowing_press = single_well_water_volume / self.productivity_index + self.res_press
        water_gravitation_head = self.water_density * self.gravitation_acc * self.depth
        water_flow_velocity = single_well_water_volume / self.xsection_area

        friction_loss = (self.friction_factor * self.depth * water_flow_velocity ** 2) / \
                        (2 * self.prod_tubing_diam * self.gravitation_const) * self.water_density
        diff_press = wellbore_flowing_press - water_gravitation_head

        pumping_press = diff_press + friction_loss - self.press_pump \
            if diff_press + friction_loss >= 0 else ureg.Quantity(0.0, "psia")
        pumping_hp_single_well = pumping_press * single_well_water_volume / self.eta_pump

        # energy-use
        water_pump_power_single_well = get_energy_consumption(self.prime_mover_type, pumping_hp_single_well)
        total_water_pump_power = water_pump_power_single_well * self.num_water_inj_wells
        energy_use = self.energy

        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, total_water_pump_power)

        # import and export
        self.set_import_from_energy(energy_use)

        # emission
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)
