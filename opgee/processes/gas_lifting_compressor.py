#
# GasLiftingCompressor class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .. import ureg
from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..log import getLogger
from ..process import Process
from ..processes.compressor import Compressor
from .shared import get_energy_carrier

_logger = getLogger(__name__)


class GasLiftingCompressor(Process):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        field = self.field
        self.gas = field.gas
        self.res_press = field.res_press
        self.prime_mover_type = self.attr("prime_mover_type")
        self.eta_compressor = self.attr("eta_compressor")
        self.gas_lifting = field.gas_lifting

    def check_enabled(self):
        if not self.gas_lifting:
            self.set_enabled(False)

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        # mass rate
        input = self.find_input_stream("lifting gas", raiseError=None)

        if input is None or input.is_uninitialized():
            return

        loss_rate = self.get_compressor_and_well_loss_rate(input)
        gas_fugitives = self.set_gas_fugitives(input, loss_rate)

        lifting_gas = self.find_output_stream("lifting gas")
        lifting_gas.copy_flow_rates_from(input)
        lifting_gas.subtract_rates_from(gas_fugitives)

        input_tp = input.tp
        discharge_press = (self.res_press + input_tp.P) / 2 + ureg.Quantity(100.0, "psia")
        overall_compression_ratio = discharge_press / input_tp.P
        energy_consumption, output_temp, _ = Compressor.get_compressor_energy_consumption(field,
                                                                                          self.prime_mover_type,
                                                                                          self.eta_compressor,
                                                                                          overall_compression_ratio,
                                                                                          input)

        lifting_gas.tp.set(T=output_temp, P=discharge_press)

        self.set_iteration_value(lifting_gas.total_flow_rate())

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
