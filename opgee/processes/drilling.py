#
# Drilling class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import numpy as np

from ..emissions import EM_LAND_USE
from ..energy import EN_DIESEL
from ..log import getLogger
from ..process import Process
from ..stream import Stream
from ..units import ureg

_logger = getLogger(__name__)


class Drilling(Process):
    """
        A class representing the drilling process in a field.

    Attributes
        fraction_wells_fractured : float
            The fraction of wells that are fractured.
        fracture_consumption_tbl : pandas.DataFrame
            The table containing fracture energy consumption data.
        pressure_gradient_fracturing : pint.Quantity
            The pressure gradient for fracturing.
        volume_per_well_fractured : pint.Quantity
            The volume per fractured well.
        oil_sands_mine : str
            The type of oil sands mine (if any).
        land_use_EF : pandas.DataFrame
            The table containing land use emission factors.
        ecosystem_richness : str
            The ecosystem richness category of the field.
        field_development_intensity : str
            The field development intensity category.
        num_water_inj_wells : int
            The number of water injection wells.
        num_wells : int
            The total number of wells (production + water injection).
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self.ecosystem_richness = None
        self.field_development_intensity = None
        self.fraction_wells_fractured = None
        self.fracture_consumption_tbl = None
        self.land_use_EF = None
        self.oil_sands_mine = None
        self.pressure_gradient_fracturing = None
        self.volume_per_well_fractured = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field

        self.fraction_wells_fractured = field.fraction_wells_fractured
        self.fracture_consumption_tbl = field.model.fracture_energy
        self.pressure_gradient_fracturing = field.pressure_gradient_fracturing
        self.volume_per_well_fractured = field.volume_per_well_fractured
        self.oil_sands_mine = field.oil_sands_mine
        self.land_use_EF = field.model.land_use_EF
        self.ecosystem_richness = field.ecosystem_richness
        self.field_development_intensity = field.field_development_intensity

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        fracture_energy_constant = self.get_fracture_constant()
        fracture_diesel_use = self.get_fracture_diesel(fracture_energy_constant)
        num_wells = field.get_process_data("num_wells")
        fracture_fuel_consumption = self.fraction_wells_fractured * num_wells * fracture_diesel_use
        fracture_energy_consumption = fracture_fuel_consumption * field.model.const("diesel-LHV")

        tot_energy_consumption = fracture_energy_consumption + field.get_process_data("drill_energy_consumption")
        wellhead_LHV_rate = field.get_process_data("wellhead_LHV_rate")
        cumulative_export_LHV = field.get_process_data("cumulative_export_LHV")
        diesel_consumption = wellhead_LHV_rate / cumulative_export_LHV * tot_energy_consumption

        # calculate land use emissions

        index_name = self.ecosystem_richness if self.oil_sands_mine == "None" else "Oil sands mining"
        land_use_intensity_df = self.land_use_EF.loc[index_name]
        land_use_intensity = land_use_intensity_df.loc[self.field_development_intensity]
        stream = Stream("stream_stp", tp=field.stp)


        oil_SG = field.oil.oil_specific_gravity
        boundary_API = field.get_process_data("boundary_API")
        if boundary_API is not None:
            oil_SG = field.oil.specific_gravity(boundary_API)
            stream.set_API(boundary_API)

        land_use_emission = \
            (land_use_intensity.sum() * field.oil_volume_rate * field.oil.volume_energy_density(
                stream,
                oil_SG,
                field.oil.gas_specific_gravity,
                field.oil.gas_oil_ratio)) if not field.offshore else ureg.Quantity(0, "tonne/day")

        # energy-use
        energy_use = self.energy
        energy_use.set_rate(EN_DIESEL, diesel_consumption)

        # emissions
        self.set_combustion_emissions()
        self.emissions.set_rate(EM_LAND_USE, "CO2", land_use_emission)

    def get_fracture_constant(self):
        """
        Calculate fracturing rig energy consumption constant a, b, c

        :return:Array list of const [a, b, c]
        """

        value = self.pressure_gradient_fracturing
        tbl = self.fracture_consumption_tbl
        result = [np.interp(value.m, tbl[col].index, tbl[col].values) for col in ['a', 'b', 'c']]

        return result

    def get_fracture_diesel(self, constants):
        """
        Calculate diesel use per well for fracturing

        :return: diesel use (unit=gallon)
        """
        variables = []
        volume = self.volume_per_well_fractured.m
        variables = [volume * volume, volume, 1]

        result = np.dot(variables, constants)
        result = ureg.Quantity(result, "gallon")
        return result
