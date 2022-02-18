from opgee.processes.compressor import Compressor
from .shared import get_energy_carrier
from .. import ureg
from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..log import getLogger
from ..process import Process
from ..import_export import ImportExport

_logger = getLogger(__name__)


class GasLiftingCompressor(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.res_press = field.attr("res_press")

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        # mass rate
        input = self.find_input_stream("lifting gas")

        if input.is_uninitialized():
            return

        loss_rate = self.venting_fugitive_rate()

        # TODO: Wennan, this intermediate copy should not be necessary
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)
        gas_fugitives.set_tp(field.stp)

        lifting_gas = self.find_output_stream("lifting gas")
        lifting_gas.copy_flow_rates_from(input)

        input_tp = input.tp

        discharge_press = (self.res_press + input_tp.P) / 2 + ureg.Quantity(100.0, "psia")
        overall_compression_ratio = discharge_press / input_tp.P
        energy_consumption, _, _ = Compressor.get_compressor_energy_consumption(field,
                                                                                field.prime_mover_type_lifting,
                                                                                field.eta_compressor_lifting,
                                                                                overall_compression_ratio,
                                                                                lifting_gas,
                                                                                inlet_tp=input.tp)

        energy_content_imported_gas = self.gas.mass_energy_density(lifting_gas) * lifting_gas.total_gas_rate()
        frac_imported_gas_consumed = energy_consumption / energy_content_imported_gas
        gas_lifting_fugitive_loss_rate = self.field.get_process_data("gas_lifting_compressor_loss_rate")
        loss_rate = (ureg.Quantity(0, "frac")
                     if gas_lifting_fugitive_loss_rate is None else gas_lifting_fugitive_loss_rate)
        factor = 1 - loss_rate - frac_imported_gas_consumed
        lifting_gas.multiply_flow_rates(factor.m)

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(field.prime_mover_type_lifting)
        energy_use.set_rate(energy_carrier, energy_consumption)

        # import/export
        import_product = ImportExport()
        import_product.add_import_from_energy(self.name, energy_use)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)

        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)

        if self.field.get_process_data("methane_from_gas_lifting") is None:
            self.field.save_process_data(methane_from_gas_lifting=lifting_gas.gas_flow_rate("C1"))
