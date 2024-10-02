#
# CrudeOilTransport class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..import_export import CRUDE_OIL
from ..log import getLogger
from ..process import Process
from .shared import get_energy_carrier

_logger = getLogger(__name__)

class CrudeOilTransport(Process):
    """
    Crude oil transport calculate emissions from crude oil to the market
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self.transport_share_fuel = self.model.transport_share_fuel.loc["Crude"]
        self.transport_parameter = self.model.transport_parameter[["Crude", "Units"]]

        self.frac_transport_mode = None
        self.transport_by_mode = None
        self.transport_dist = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field
        self.frac_transport_mode = field.attrs_with_prefix("frac_transport_").rename("Fraction")
        self.transport_dist = field.attrs_with_prefix("transport_dist_").rename("Distance")
        self.transport_by_mode = self.frac_transport_mode.to_frame().join(self.transport_dist)

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        input_oil = self.find_input_stream("oil")

        if input_oil.is_uninitialized():
            return

        oil_mass_rate = input_oil.liquid_flow_rate("oil")
        oil_mass_energy_density = self.oil.mass_energy_density()
        oil_LHV_rate = oil_mass_rate * oil_mass_energy_density

        if self.field.get_process_data("crude_LHV") is None:
            self.field.save_process_data(crude_LHV=oil_mass_energy_density)

        output = self.find_output_stream("oil")
        output.copy_flow_rates_from(input_oil)

        # energy use
        fuel_consumption = field.transport_energy.get_transport_energy_dict(self.field,
                                                                            self.transport_parameter,
                                                                            self.transport_share_fuel,
                                                                            self.transport_by_mode,
                                                                            oil_LHV_rate,
                                                                            "Crude")
        energy_use = self.energy
        for name, value in fuel_consumption.items():
            energy_use.set_rate(get_energy_carrier(name), value.to("mmBtu/day"))

        # import/export
        self.set_import_from_energy(energy_use)
        field.import_export.set_export(self.name, CRUDE_OIL, oil_LHV_rate)

        # emissions
        self.set_combustion_emissions()
