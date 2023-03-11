#
# GasReinjectionCompressor class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .compressor import Compressor
from .shared import get_energy_carrier
from .. import ureg

from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class GasReinjectionCompressor(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.res_press = field.res_press
        self.prime_mover_type = self.attr("prime_mover_type")
        self.eta_compressor = self.attr("eta_compressor")
        self.natural_gas_reinjection = field.natural_gas_reinjection
        self.gas_flooding = field.gas_flooding

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas for gas reinjection compressor", raiseError=False)
        if input is None or (not self.natural_gas_reinjection and not self.gas_flooding):
            self.set_enabled(False)
            return

        if input.is_uninitialized():
            return

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives = self.set_gas_fugitives(input, loss_rate)

        gas_to_well = self.find_output_stream("gas for gas reinjection well")
        gas_to_well.copy_flow_rates_from(input)
        gas_to_well.subtract_rates_from(gas_fugitives)

        discharge_press = self.res_press + ureg.Quantity(500., "psi")
        overall_compression_ratio = discharge_press / input.tp.P
        energy_consumption, output_temp, _ = Compressor.get_compressor_energy_consumption(
            self.field,
            self.prime_mover_type,
            self.eta_compressor,
            overall_compression_ratio,
            input)

        gas_to_well.tp.set(T=output_temp, P=discharge_press)

        self.set_iteration_value(gas_to_well.total_flow_rate())

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, energy_consumption)

        # import/export
        self.set_import_from_energy(energy_use)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)

        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
