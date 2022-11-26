#
# GasPartition class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .shared import get_init_lifting_stream
from .. import ureg
from ..combine_streams import combine_streams
from ..core import STP
from ..core import TemperaturePressure
from ..error import OpgeeException
from ..import_export import N2, CO2_Flooding, NATURAL_GAS
from ..log import getLogger
from ..process import Process
from ..stream import PHASE_GAS, Stream

_logger = getLogger(__name__)


class GasPartition(Process):
    """
    Gas partition is to check the reasonable amount of gas goes to gas lifting and gas reinjection
    """

    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.gas_lifting = field.attr("gas_lifting")

        self.CO2_source = self.attr("CO2_source")
        self.impurity_CH4_in_CO2 = self.attr("impurity_CH4_in_CO2")
        self.impurity_N2_in_CO2 = self.attr("impurity_N2_in_CO2")

        self.imported_NG_comp = field.imported_gas_comp["NG Flooding"]
        self.imported_NG_mass_frac = field.gas.component_mass_fractions(self.imported_NG_comp)
        self.API = field.attr("API")

        self.fraction_remaining_gas_inj = field.attr("fraction_remaining_gas_inj")
        self.natural_gas_reinjection = field.attr("natural_gas_reinjection")
        self.gas_flooding = field.attr("gas_flooding")
        self.flood_gas_type = field.attr("flood_gas_type")
        self.GLIR = field.attr("GLIR")
        self.oil_prod = field.attr("oil_prod")
        self.WOR = field.attr("WOR")
        self.iteration_tolerance = field.model.attr("iteration_tolerance")
        self.flood_gas_type = field.attr("flood_gas_type")
        self.N2_flooding_tp = TemperaturePressure(self.attr("N2_flooding_temp"),
                                                  self.attr("N2_flooding_press"))
        self.C1_flooding_tp = TemperaturePressure(self.attr("C1_flooding_temp"),
                                                  self.attr("C1_flooding_press"))
        self.CO2_flooding_tp = TemperaturePressure(self.attr("CO2_flooding_temp"),
                                                   self.attr("CO2_flooding_press"))

        self.GFIR = field.attr("GFIR")
        self.oil_prod = field.attr("oil_prod")
        self.gas_flooding_vol_rate = self.oil_prod * self.GFIR
        self.gas_lifting_vol_rate = self.oil_prod * (1 + self.WOR) * self.GLIR
        self.is_first_loop = True

    def run(self, analysis):
        self.print_running_msg()
        field = self.field
        import_product = field.import_export

        reinjected_gas_stream = Stream("reinjected_gas_stream", tp=field.stp)
        exported_gas_stream = Stream("exported_gas_stream", tp=field.stp)

        input = self.find_input_stream("gas for gas partition", raiseError=False)

        if input is None:
            if self.gas_flooding:
                self.gas_flooding_setup(import_product, reinjected_gas_stream, exported_gas_stream, input)
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

                # Check
                iteration_series = (lifting_gas_to_compressor.components.gas - input.components.gas).astype(float)
                iteration_series[iteration_series < 0] = 0
                self.set_iteration_value(iteration_series)

                if sum(iteration_series) >= self.iteration_tolerance:
                    lifting_gas_to_compressor.copy_flow_rates_from(input)
                    return

                exported_gas_stream.subtract_rates_from(lifting_gas_to_compressor, PHASE_GAS)
                input.subtract_rates_from(lifting_gas_to_compressor, PHASE_GAS)

            if self.gas_flooding:
                self.gas_flooding_setup(import_product, reinjected_gas_stream, exported_gas_stream, input)

            elif self.natural_gas_reinjection:
                reinjected_gas_stream.copy_flow_rates_from(input)
                reinjected_gas_stream.multiply_flow_rates(self.fraction_remaining_gas_inj)
                exported_gas_stream.subtract_rates_from(reinjected_gas_stream, PHASE_GAS)

                gas_to_reinjection = self.find_output_stream("gas for gas reinjection compressor")
                gas_to_reinjection.copy_flow_rates_from(reinjected_gas_stream)

        exported_gas = self.find_output_stream("gas")
        exported_gas.copy_flow_rates_from(exported_gas_stream)
        field.save_process_data(exported_gas=exported_gas)

    def gas_flooding_setup(self, import_product, reinjected_gas_stream, exported_gas_stream, input_stream):
        field = self.field

        known_types = ["N2", "NG", "CO2"]
        if self.flood_gas_type not in known_types:
            raise OpgeeException(f"{self.flood_gas_type} is not in the known gas type: {known_types}")

        if self.flood_gas_type == "N2":
            N2_mass_rate = self.gas_flooding_vol_rate * field.gas.component_gas_rho_STP["N2"]
            reinjected_gas_stream.set_gas_flow_rate("N2", N2_mass_rate)
            reinjected_gas_stream.set_tp(self.N2_flooding_tp)

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
            if input_stream is None:
                total_gas_rate = ureg.Quantity(0, "tonne/day")
            else:
                total_gas_rate = input_stream.total_gas_rate()
                input_STP.copy_flow_rates_from(input_stream, tp=STP)

            NG_mass_rate = self.gas_flooding_vol_rate * field.gas.density(input_STP)

            # The mass of produced processed NG is enough for NG flooding
            if NG_mass_rate < total_gas_rate:
                reinjected_gas_series = \
                    NG_mass_rate * field.gas.component_mass_fractions(field.gas.component_molar_fractions(input_stream))
                reinjected_gas_stream.set_rates_from_series(reinjected_gas_series, PHASE_GAS)
                reinjected_gas_stream.set_tp(input_stream.tp)
                exported_gas_stream.subtract_rates_from(reinjected_gas_stream, PHASE_GAS)

            # The imported NG is need for NG flooding
            else:
                imported_NG_series = (NG_mass_rate - total_gas_rate) * self.imported_NG_mass_frac
                imported_NG_stream = Stream("imported_NG_stream", tp=self.N2_flooding_tp)
                imported_NG_stream.set_rates_from_series(imported_NG_series, PHASE_GAS)
                imported_NG_energy_rate = field.gas.energy_flow_rate(imported_NG_stream)

                reinjected_gas_stream = imported_NG_stream
                if input_stream is not None:
                    reinjected_gas_stream = combine_streams([imported_NG_stream, input_stream], API=self.API)
                exported_gas_stream.reset()
                exported_gas_stream.set_tp(tp=STP)
                import_product.set_import(self.name, NATURAL_GAS, imported_NG_energy_rate)

        gas_to_reinjection = self.find_output_stream("gas for gas reinjection compressor")
        if reinjected_gas_stream.total_flow_rate().m != 0:
            gas_to_reinjection.copy_flow_rates_from(reinjected_gas_stream)
