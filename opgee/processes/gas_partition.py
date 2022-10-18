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
        self.imported_fuel_gas_mol_frac = field.imported_gas_comp["Imported Fuel"]
        self.imported_fuel_gas_mass_frac = field.gas.component_mass_fractions(self.imported_fuel_gas_mol_frac)
        self.imported_gas_stream = Stream("imported_gas", STP)
        self.imported_gas_stream.set_rates_from_series(
            self.imported_fuel_gas_mass_frac * ureg.Quantity(1., "tonne/day"),
            phase=PHASE_GAS)

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
        self.offset_gas_comp = field.imported_gas_comp["NG Flooding"]
        self.oil_prod = field.attr("oil_prod")
        self.gas_flooding_vol_rate = self.oil_prod * self.GFIR
        self.gas_lifting_vol_rate = self.oil_prod * (1 + self.WOR) * self.GLIR
        self.is_first_loop = True

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        if not self.all_streams_ready("gas for gas partition"):
            return

        input = self.find_input_streams("gas for gas partition", combine=True)
        if input.is_uninitialized():
            return

        reinjected_gas_stream = Stream("reinjected_gas_stream", tp=input.tp)
        exported_gas_stream = Stream("exported_gas_stream", tp=input.tp)
        exported_gas_stream.copy_flow_rates_from(input)

        if self.gas_flooding:

            import_product = field.import_export

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
                if field.get_process_data("CO2_reinjection_mass_rate") is not None:
                    CO2_mass_rate = max(ureg.Quantity(0, "tonne/day"),
                                        CO2_mass_rate - field.get_process_data("CO2_reinjection_mass_rate"))
                if field.get_process_data("sour_gas_reinjection_mass_rate") is not None:
                    CO2_mass_rate = max(ureg.Quantity(0, "tonne/day"),
                                        CO2_mass_rate - field.get_process_data("sour_gas_reinjection_mass_rate"))

                if self.CO2_source == "Natural subsurface reservoir":
                    impurity_mass_rate = CO2_mass_rate * self.impurity_CH4_in_CO2
                    reinjected_gas_stream.set_gas_flow_rate("C1", impurity_mass_rate)
                else:
                    impurity_mass_rate = CO2_mass_rate * self.impurity_N2_in_CO2
                    reinjected_gas_stream.set_gas_flow_rate("N2", impurity_mass_rate)
                reinjected_gas_stream.set_gas_flow_rate("CO2", CO2_mass_rate)
                reinjected_gas_stream.set_tp(self.CO2_flooding_tp)

                import_product.set_import(self.name, CO2_Flooding, CO2_mass_rate + impurity_mass_rate)
            else:
                input_STP = Stream("input_stream_at_STP", tp=STP)
                input_STP.copy_flow_rates_from(input, tp=STP)
                NG_mass_rate = self.gas_flooding_vol_rate * field.gas.density(input_STP)

                # The mass of produced processed NG is enough for NG flooding
                if NG_mass_rate < input.total_gas_rate():
                    reinjected_gas_series = \
                        NG_mass_rate * field.gas.component_mass_fractions(field.gas.component_molar_fractions(input))
                    reinjected_gas_stream.set_rates_from_series(reinjected_gas_series, PHASE_GAS)
                    reinjected_gas_stream.set_tp(input.tp)
                    exported_gas_stream.subtract_rates_from(reinjected_gas_stream, PHASE_GAS)

                # The imported NG is need for NG flooding
                else:
                    imported_NG_series = (NG_mass_rate - input.total_gas_rate()) * self.imported_NG_mass_frac
                    imported_NG_stream = Stream("imported_NG_stream", tp=self.N2_flooding_tp)
                    imported_NG_stream.set_rates_from_series(imported_NG_series, PHASE_GAS)
                    imported_NG_energy_rate = field.gas.energy_flow_rate(imported_NG_stream)

                    reinjected_gas_stream = combine_streams([imported_NG_stream, input], API=self.API)
                    exported_gas_stream.reset()
                    exported_gas_stream.set_tp(tp=STP)
                    import_product.set_import(self.name, NATURAL_GAS, imported_NG_energy_rate)

            gas_to_reinjection = self.find_output_stream("gas for gas reinjection compressor")
            gas_to_reinjection.copy_flow_rates_from(reinjected_gas_stream)

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
                self.field.save_process_data(lifting_gas_stream=lifting_gas_to_compressor)
                return

            exported_gas_stream.subtract_rates_from(lifting_gas_to_compressor, PHASE_GAS)

        exported_gas = self.find_output_stream("gas")
        exported_gas.copy_flow_rates_from(exported_gas_stream)

        #
        # exported_gas = self.find_output_stream("gas")
        # exported_gas.copy_flow_rates_from(input, tp=input_tp)
        # if gas_lifting:
        #     exported_gas.subtract_rates_from(gas_lifting)

        # gas_to_reinjection = self.find_output_stream("gas for gas reinjection compressor", raiseError=False)
        # if gas_to_reinjection:
        #     if self.natural_gas_reinjection or (self.gas_flooding and self.flood_gas_type == "NG"):
        #         gas_to_reinjection.copy_flow_rates_from(exported_gas)
        #         gas_to_reinjection.multiply_flow_rates(self.fraction_remaining_gas_inj)

        # TODO: fix the following lines

        # elif self.flood_gas_type == "NG":
        #     adjust_flow_vol_rate = self.gas_flooding_vol_rate \
        #         if self.gas_flooding_vol_rate.m <= input_gas_vol_rate.m \
        #         else self.gas_flooding_vol_rate - input_gas_vol_rate
        #     offset_mass_frac = field.gas.component_mass_fractions(self.offset_gas_comp)
        #     offset_density = field.gas.component_gas_rho_STP[self.offset_gas_comp.index]
        #     reinjected_gas_stream.set_rates_from_series(adjust_flow_vol_rate * offset_mass_frac * offset_density,
        #                                        phase=PHASE_GAS)
        #     reinjected_gas_stream.set_tp(self.C1_flooding_tp)
        #
        #     # Calculate import NG energy content
        #     gas_mass_rate = reinjected_gas_stream.total_gas_rate()
        #     gas_mass_energy_density = self.gas.mass_energy_density(reinjected_gas_stream)
        #     gas_LHV_rate = gas_mass_rate * gas_mass_energy_density
        #     import_product = field.import_export
        #     import_product.set_import(self.name, NATURAL_GAS, gas_LHV_rate)
        # else:
        #     CO2_mass_rate = self.gas_flooding_vol_rate * field.gas.component_gas_rho_STP["CO2"]
        #     reinjected_gas_stream.set_gas_flow_rate("CO2", CO2_mass_rate)
        #     reinjected_gas_stream.set_tp(self.N2_flooding_tp)
        #
        # combine_streams([total_rate_for_compression, reinjected_gas_stream])

        # gas_mass_rate = exported_gas.total_gas_rate()
        # gas_mass_energy_density = self.gas.mass_energy_density(exported_gas)
        # gas_LHV_rate = gas_mass_rate * gas_mass_energy_density
        # import_product = field.import_export
        # import_product.set_export(self.name, NATURAL_GAS, gas_LHV_rate)

        # excluded = [s.strip() for s in getParam("OPGEE.ExcludeFromReinjectionEnergySummary").split(",")]
        # energy_sum = self.field.sum_process_energy(processes_to_exclude=excluded)
        # NG_energy_sum = energy_sum.get_rate(EN_NATURAL_GAS)
        #
        # NG_LHV = self.gas.mass_energy_density(gas_to_reinjection)
        # is_gas_to_reinjection_empty = False
        # if NG_LHV.m == 0:
        #     is_gas_to_reinjection_empty = True
        #     NG_LHV = self.gas.mass_energy_density(self.reinjected_gas_stream)
        #
        # NG_mass = NG_energy_sum / NG_LHV
        # NG_consumption_stream = Stream("NG_consump_stream", gas_to_reinjection.tp)
        #
        # if is_gas_to_reinjection_empty:
        #     NG_consumption_series = self.imported_fuel_gas_mass_fracs * NG_mass
        # else:
        #     NG_consumption_series = self.gas.component_mass_fractions(
        #         self.gas.component_molar_fractions(gas_to_reinjection)) * NG_mass
        #
        # NG_consumption_stream.set_rates_from_series(NG_consumption_series, PHASE_GAS)
        #
        # tot_exported_mass = gas_to_reinjection.total_flow_rate() - NG_consumption_stream.total_flow_rate()
        # if tot_exported_mass.m >= 0:
        #     exported_gas.copy_flow_rates_from(gas_to_reinjection)
        #     exported_gas.subtract_gas_rates_from(NG_consumption_stream)
        #     exported_gas.set_tp(input_tp)
        #
        # if is_gas_to_reinjection_empty is False and tot_exported_mass.m >= 0:
        #     gas_to_reinjection.subtract_gas_rates_from(exported_gas)
