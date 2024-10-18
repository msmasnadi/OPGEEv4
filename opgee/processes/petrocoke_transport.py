#
# PetrocokeTransport class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..import_export import NGL_LPG
from ..log import getLogger
from ..process import Process
from .shared import get_energy_carrier

_logger = getLogger(__name__)


class PetrocokeTransport(Process):
    """
    Petrocoke transport calculate emissions from petrocoke to the market
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        model = self.model
        self.transport_share_fuel = model.transport_share_fuel.loc["Petrocoke"]
        self.transport_parameter = model.transport_parameter[["Petrocoke", "Units"]]
        self.transport_by_mode = model.transport_by_mode.loc["Petrocoke"]
        self.petro_coke_heating_value = model.const("petrocoke-heating-value")

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        input_coke = self.find_input_stream("petrocoke")

        if input_coke.is_uninitialized():
            return

        petrocoke_mass_rate = input_coke.solid_flow_rate("PC")
        petrocoke_LHV_rate = petrocoke_mass_rate * self.petro_coke_heating_value

        petrocoke_to_market = self.find_output_stream("petrocoke")
        petrocoke_to_market.copy_flow_rates_from(input_coke)

        # energy use
        energy_use = self.energy
        fuel_consumption = \
            field.transport_energy.get_transport_energy_dict(self.field,
                                                             self.transport_parameter,
                                                             self.transport_share_fuel,
                                                             self.transport_by_mode,
                                                             petrocoke_LHV_rate,
                                                             "Petrocoke")

        for name, value in fuel_consumption.items():
            energy_use.set_rate(get_energy_carrier(name), value.to("mmBtu/day"))

        # import/export
        import_product = field.import_export
        self.set_import_from_energy(energy_use)
        import_product.set_export(self.name, NGL_LPG, petrocoke_LHV_rate)

        # emissions
        self.set_combustion_emissions()
