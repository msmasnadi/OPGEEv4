#
# LNGTransport class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..emissions import EM_COMBUSTION
from ..import_export import NGL_LPG
from ..log import getLogger
from ..process import Process
from ..processes.transport_energy import TransportEnergy
from .shared import get_energy_carrier

_logger = getLogger(__name__)


class LNGTransport(Process):
    """
    LNG transport calculate emissions from LNG to the marketåœ
    """

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.transport_share_fuel = self.model.transport_share_fuel.loc["LNG"]
        self.transport_parameter = self.model.transport_parameter[["LNG", "Units"]]
        self.transport_by_mode = self.model.transport_by_mode.loc["LNG"]

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        input = self.find_input_stream("gas for transport")

        if input.is_uninitialized():
            return

        gas_mass_rate = input.total_gas_rate()
        gas_mass_energy_density = self.gas.mass_energy_density(input)
        gas_LHV_rate = gas_mass_rate * gas_mass_energy_density

        output = self.find_output_stream("gas")
        output.copy_flow_rates_from(input)

        # energy use
        energy_use = self.energy
        fuel_consumption = field.transport_energy.get_transport_energy_dict(self.field,
                                                                            self.transport_parameter,
                                                                            self.transport_share_fuel,
                                                                            self.transport_by_mode,
                                                                            gas_LHV_rate,
                                                                            "LNG")

        for name, value in fuel_consumption.items():
            energy_use.set_rate(get_energy_carrier(name), value.to("mmBtu/day"))

        # import/export
        import_product = field.import_export
        self.set_import_from_energy(energy_use)
        import_product.set_export(self.name, NGL_LPG, gas_LHV_rate)

        # emission
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)
