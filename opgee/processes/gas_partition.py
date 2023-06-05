#
# GasPartition class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .. import ureg
from ..core import STP
from ..core import TemperaturePressure
from ..error import OpgeeException
from ..energy import EN_NATURAL_GAS
from ..import_export import N2, CO2_Flooding, NATURAL_GAS
from ..log import getLogger
from ..process import Process
from ..stream import PHASE_GAS, Stream
from ..constants import mol_per_scf
from .shared import get_init_lifting_stream

_logger = getLogger(__name__)


class GasPartition(Process):
    """
    Gas partition is to check the reasonable amount of gas goes to gas lifting and gas reinjection
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        field = self.field
        self.gas = field.gas
        self.gas_lifting = field.gas_lifting

        self.CO2_source = self.attr("CO2_source")
        self.impurity_CH4_in_CO2 = self.attr("impurity_CH4_in_CO2")
        self.impurity_N2_in_CO2 = self.attr("impurity_N2_in_CO2")

        self.imported_NG_comp = field.imported_gas_comp["NG Flooding"]
        self.imported_NG_mass_frac = field.gas.component_mass_fractions(self.imported_NG_comp)

        self.fraction_remaining_gas_inj = field.fraction_remaining_gas_inj
        self.natural_gas_reinjection = field.natural_gas_reinjection
        self.gas_flooding = field.gas_flooding
        self.flood_gas_type = field.flood_gas_type
        self.GLIR = field.GLIR
        self.oil_volume_rate = field.oil_volume_rate
        self.WOR = field.WOR
        self.iteration_tolerance = field.model.attr("iteration_tolerance")
        self.flood_gas_type = field.flood_gas_type
        self.N2_flooding_tp = TemperaturePressure(self.attr("N2_flooding_temp"),
                                                  self.attr("N2_flooding_press"))
        self.C1_flooding_tp = TemperaturePressure(self.attr("C1_flooding_temp"),
                                                  self.attr("C1_flooding_press"))
        self.CO2_flooding_tp = TemperaturePressure(self.attr("CO2_flooding_temp"),
                                                   self.attr("CO2_flooding_press"))

        self.GFIR = field.GFIR
        self.gas_flooding_vol_rate = self.oil_volume_rate * self.GFIR
        self.gas_lifting_vol_rate = self.oil_volume_rate * (1 + self.WOR) * self.GLIR
        self.is_first_loop = True
        self.reset_flag = False

    def run(self, analysis):
        self.print_running_msg()
        field = self.field
        import_product = field.import_export

        reinjected_gas_stream = Stream("reinjected_gas_stream", tp=field.stp)
        exported_gas_stream = Stream("exported_gas_stream", tp=field.stp)

        input = self.find_input_stream("gas for gas partition", raiseError=False)

        if input is None:
            if self.gas_flooding:
                self.gas_flooding_setup(import_product, reinjected_gas_stream, exported_gas_stream)
                self.set_iteration_value(reinjected_gas_stream.total_flow_rate())

            exported_gas_stream.set_tp(STP)
        else:
            if not self.all_streams_ready("gas for gas partition"):
                return

            input = self.find_input_streams("gas for gas partition", combine=True)
            if input.is_uninitialized():
                return
            exported_gas_stream.copy_flow_rates_from(input)

            if self.gas_lifting:
                lifting_gas_to_compressor = self.find_output_stream("lifting gas")
                if self.is_first_loop:
                    init_stream = get_init_lifting_stream(self.field.gas,
                                                          input,
                                                          self.gas_lifting_vol_rate)
                    lifting_gas_to_compressor.copy_flow_rates_from(init_stream)
                    self.is_first_loop = False


                iteration_series = (lifting_gas_to_compressor.components.gas - input.components.gas).astype(float)
                iteration_series[iteration_series < 0] = 0

                if sum(iteration_series) >= self.iteration_tolerance:
                    self.set_iteration_value(iteration_series)
                    lifting_gas_to_compressor.copy_flow_rates_from(input)
                    return

                exported_gas_stream.subtract_rates_from(lifting_gas_to_compressor, PHASE_GAS)

            if self.gas_flooding:
                self.gas_flooding_setup(import_product, reinjected_gas_stream, exported_gas_stream)

            elif self.natural_gas_reinjection:
                NG_energy_flow_rate_needed = field.import_export.import_df[EN_NATURAL_GAS].sum()
                reinjected_gas_energy_flow_rate = field.gas.energy_flow_rate(exported_gas_stream)
                if reinjected_gas_energy_flow_rate <= NG_energy_flow_rate_needed:
                    reinjected_gas_stream.reset()
                    reinjected_gas_stream.set_tp(exported_gas_stream.tp)
                    exported_gas_stream.reset()
                    exported_gas_stream.set_tp(reinjected_gas_stream.tp)
                else:
                    fuel_stream = Stream("fuel_stream", tp=exported_gas_stream.tp)
                    fuel_stream.copy_flow_rates_from(exported_gas_stream)
                    fuel_fraction = NG_energy_flow_rate_needed / reinjected_gas_energy_flow_rate
                    fuel_stream.multiply_flow_rates(fuel_fraction)

                    reinjected_gas_stream.copy_flow_rates_from(exported_gas_stream)
                    reinjected_gas_stream.multiply_flow_rates(self.fraction_remaining_gas_inj)
                    reinjected_gas_stream.subtract_rates_from(fuel_stream)

                    exported_gas_stream.subtract_rates_from(reinjected_gas_stream)
                    exported_gas_stream.subtract_rates_from(fuel_stream)

                gas_to_reinjection = self.find_output_stream("gas for gas reinjection compressor")
                gas_to_reinjection.copy_flow_rates_from(reinjected_gas_stream)
                field.save_process_data(NG_energy_rate_consumption=min(NG_energy_flow_rate_needed,
                                                                       reinjected_gas_energy_flow_rate))

        exported_gas = self.find_output_stream("gas")
        exported_gas.copy_flow_rates_from(exported_gas_stream)
        field.save_process_data(exported_gas=exported_gas)
        if self.gas_lifting and not self.reset_flag:
            self.reset_iteration()
            self.reset_flag = True
        self.set_iteration_value(exported_gas.total_flow_rate())

    def gas_flooding_setup(self, import_product, reinjected_gas_stream, exported_gas_stream):
        field = self.field

        known_types = ["N2", "NG", "CO2"]
        if self.flood_gas_type not in known_types:
            raise OpgeeException(f"{self.flood_gas_type} is not in the known gas type: {known_types}")

        if self.flood_gas_type == "N2":
            N2_mass_rate = self.gas_flooding_vol_rate * field.gas.component_gas_rho_STP["N2"]
            reinjected_gas_stream.set_gas_flow_rate("N2", N2_mass_rate)
            reinjected_gas_stream.set_tp(self.N2_flooding_tp)
            field.save_process_data(N2_reinjection_volume_rate=self.gas_flooding_vol_rate)

            import_product.set_import(self.name, N2, N2_mass_rate)
        elif self.flood_gas_type == "CO2":
            CO2_mass_rate = self.gas_flooding_vol_rate * field.gas.component_gas_rho_STP["CO2"]
            if field.get_process_data("CO2_flooding_rate_init") is None:
                field.save_process_data(CO2_flooding_rate_init=CO2_mass_rate)
            CO2_reinjection_mass_rate = field.get_process_data("CO2_reinjection_mass_rate")
            sour_gas_reinjection_mass_rate = field.get_process_data("sour_gas_reinjection_mass_rate")
            if CO2_reinjection_mass_rate:
                CO2_mass_rate = max(ureg.Quantity(0, "tonne/day"), CO2_mass_rate - CO2_reinjection_mass_rate)
            if sour_gas_reinjection_mass_rate:
                CO2_mass_rate = max(ureg.Quantity(0, "tonne/day"), CO2_mass_rate - sour_gas_reinjection_mass_rate)

            if self.CO2_source == "Natural subsurface reservoir":
                impurity_mass_rate = CO2_mass_rate * self.impurity_CH4_in_CO2
                reinjected_gas_stream.set_gas_flow_rate("C1", impurity_mass_rate)
            else:
                impurity_mass_rate = CO2_mass_rate * self.impurity_N2_in_CO2
                reinjected_gas_stream.set_gas_flow_rate("N2", impurity_mass_rate)
            reinjected_gas_stream.set_gas_flow_rate("CO2", CO2_mass_rate)
            reinjected_gas_stream.set_tp(self.CO2_flooding_tp)

            import_product.set_import(self.name, CO2_Flooding, CO2_mass_rate + impurity_mass_rate)
            field.save_process_data(CO2_mass_rate=CO2_mass_rate)
        else:
            input_STP = Stream("input_stream_at_STP", tp=STP)
            if exported_gas_stream is None:
                exported_gas_mass_rate = ureg.Quantity(0, "tonne/day")
            else:
                exported_gas_mass_rate = exported_gas_stream.total_gas_rate()
                input_STP.copy_flow_rates_from(exported_gas_stream, tp=STP)

            exported_gas_volume_rate = exported_gas_mass_rate / field.gas.density(input_STP)

            NG_flooding_volume_rate = self.gas_flooding_vol_rate

            # The mass of produced processed NG is enough for NG flooding
            if NG_flooding_volume_rate < exported_gas_volume_rate:
                NG_flooding_mass_rate = NG_flooding_volume_rate * field.gas.density(input_STP)
                reinjected_gas_series = \
                    NG_flooding_mass_rate * field.gas.component_mass_fractions(field.gas.component_molar_fractions(exported_gas_stream))
                reinjected_gas_stream.set_rates_from_series(reinjected_gas_series, PHASE_GAS)
                reinjected_gas_stream.set_tp(exported_gas_stream.tp)
                exported_gas_stream.subtract_rates_from(reinjected_gas_stream, PHASE_GAS)

            # The imported NG is need for NG flooding
            else:
                imported_NG_series =\
                    (NG_flooding_volume_rate - exported_gas_volume_rate) * self.imported_NG_comp * mol_per_scf
                imported_NG_series *= field.gas.component_MW[imported_NG_series.index]
                imported_NG_stream = Stream("imported_NG_stream", tp=self.C1_flooding_tp)
                imported_NG_stream.set_rates_from_series(imported_NG_series, PHASE_GAS)
                imported_NG_energy_rate = field.gas.energy_flow_rate(imported_NG_stream)

                reinjected_gas_stream = imported_NG_stream
                if exported_gas_stream is not None:
                    reinjected_gas_stream.add_flow_rates_from(exported_gas_stream)
                exported_gas_stream.reset()
                exported_gas_stream.set_tp(tp=STP)
                import_product.set_import(self.name, NATURAL_GAS, imported_NG_energy_rate)

        gas_to_reinjection = self.find_output_stream("gas for gas reinjection compressor")
        if reinjected_gas_stream.total_flow_rate().m != 0:
            gas_to_reinjection.copy_flow_rates_from(reinjected_gas_stream)
