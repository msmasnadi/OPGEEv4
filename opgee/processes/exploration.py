#
# Exploration class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import math

from ..energy import EN_DIESEL
from ..log import getLogger
from ..process import Process
from ..units import ureg

_logger = getLogger(__name__)


class Exploration(Process):
    """
        The Exploration class represents the exploration phase of an oil field project.

        This class calculates the energy consumption and emissions associated with
        drilling, surveying, and transporting crude oil during the exploration phase.
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        field = self.field
        self.vertical_drill_df = field.vertical_drill_df
        self.horizontal_drill_df = field.horizontal_drill_df
        self.transport_parameter = self.model.transport_parameter[["Crude", "Units"]]

        self.depth = None
        self.distance_survey = None
        self.drill_energy_consumption = None
        self.drill_fuel_consumption = None
        self.eta_rig = None
        self.field_production_lifetime = None
        self.frac_wells_horizontal = None
        self.horizontal_drill_energy_intensity = None
        self.length_lateral = None
        self.num_gas_inj_wells = None
        self.num_water_inj_wells = None
        self.num_wells = None
        self.number_wells_dry = None
        self.number_wells_exploratory = None
        self.offshore = None
        self.oil_sands_mine = None
        self.vertical_drill_energy_intensity = None
        self.weight_land_survey = None
        self.weight_ocean_survey = None
        self.well_complexity = None
        self.well_size = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field

        self.well_size = field.well_size
        self.well_complexity = field.well_complexity
        self.eta_rig = field.eta_rig
        self.vertical_drill_energy_intensity = \
            (self.vertical_drill_df.loc[self.eta_rig]).loc[self.well_size][self.well_complexity]
        self.horizontal_drill_energy_intensity = \
            (self.horizontal_drill_df.loc[self.eta_rig]).loc[self.well_size][self.well_complexity]

        self.oil_sands_mine = field.oil_sands_mine
        self.offshore = field.offshore
        self.weight_land_survey = field.weight_land_survey
        self.weight_ocean_survey = field.weight_ocean_survey
        self.distance_survey = field.distance_survey
        self.number_wells_dry = field.number_wells_dry
        self.number_wells_exploratory = field.number_wells_exploratory

        num_prod_wells = field.num_prod_wells if self.oil_sands_mine == "None" else 0
        self.num_gas_inj_wells = 0.25 * num_prod_wells if field.natural_gas_reinjection or field.gas_flooding else 0
        self.num_water_inj_wells = field.num_water_inj_wells
        self.num_wells = math.ceil(num_prod_wells + self.num_water_inj_wells + self.num_gas_inj_wells)

        self.depth = field.depth
        self.frac_wells_horizontal = field.frac_wells_horizontal
        self.length_lateral = field.length_lateral
        self.field_production_lifetime = field.field_production_lifetime

        self.drill_fuel_consumption = \
            (self.vertical_drill_energy_intensity * (1 - self.frac_wells_horizontal) * self.depth +
             self.horizontal_drill_energy_intensity * self.frac_wells_horizontal * self.length_lateral) * self.num_wells
        self.drill_energy_consumption = field.model.const("diesel-LHV") * self.drill_fuel_consumption

    def run(self, analysis):
        self.print_running_msg()

        field = self.field
        m = self.model

        oil_mass_energy_density = field.oil.mass_energy_density()
        if self.field.get_process_data("crude_LHV") is None:
            self.field.save_process_data(crude_LHV=oil_mass_energy_density)

        ocean_tank_energy_intensity = \
            field.transport_energy.get_ocean_tanker_dest_energy_intensity(self.transport_parameter)
        truck_energy_intensity = field.transport_energy.energy_intensity_truck

        export_LHV = field.get_process_data("exported_prod_LHV")
        cumulative_export_LHV = export_LHV * self.field_production_lifetime * m.const("days-per-year")

        survey_vehicle_energy_consumption = (truck_energy_intensity * self.weight_land_survey *
                                             self.distance_survey if not self.offshore else
                                             ocean_tank_energy_intensity * self.weight_ocean_survey *
                                             self.distance_survey)

        drill_consumption_per_well = (self.drill_energy_consumption / self.num_wells
                                      if self.oil_sands_mine == "None" else ureg.Quantity(0.0, "mmbtu"))

        drill_energy_consumption = drill_consumption_per_well * (self.number_wells_dry + self.number_wells_exploratory)
        frac_energy_consumption = (survey_vehicle_energy_consumption + drill_energy_consumption) / cumulative_export_LHV
        diesel_consumption = frac_energy_consumption * export_LHV

        field.save_process_data(cumulative_export_LHV=cumulative_export_LHV)
        field.save_process_data(drill_energy_consumption=self.drill_energy_consumption)
        field.save_process_data(num_wells=self.num_wells)

        # energy-use
        energy_use = self.energy
        energy_use.set_rate(EN_DIESEL, diesel_consumption)

        # emissions
        self.set_combustion_emissions()
