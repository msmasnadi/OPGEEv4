#
# CrudeOilTransport class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import pandas as pd

from .. import ureg
from ..core import STP, TemperaturePressure
from ..emissions import EM_FUGITIVES
from ..energy import EN_ELECTRICITY
from ..log import getLogger
from ..process import Process
from ..process import run_corr_eqns
from ..stream import PHASE_GAS, Stream
from .compressor import Compressor
from .shared import get_energy_carrier, predict_blower_energy_use, get_bounded_value

_logger = getLogger(__name__)


class Demethanizer(Process):
    """
    A class to represent the Demethanizer process, which is responsible for separating
    methane from heavier hydrocarbons (NGL) and producing a methane-rich gas stream
    and a heavier hydrocarbon stream (LPG).

    Attributes
       feed_press_demethanizer : pint.Quantity
           The pressure of the feed gas entering the demethanizer column.
       column_pressure : pint.Quantity
           The pressure inside the demethanizer column.
       methane_to_LPG_ratio : pint.Quantity
           The desired ratio of methane to LPG in the product streams.
       demethanizer_tbl : pd.DataFrame
           The demethanizer table containing correlation equations for the process.
       mol_per_scf : pint.Quantity
           The conversion factor for moles to standard cubic feet.
       eta_reboiler_demethanizer : pint.Quantity
           The efficiency of the reboiler in the demethanizer column.
       air_cooler_speed_reducer_eff : pint.Quantity
           The efficiency of the speed reducer in the air cooler.
       air_cooler_delta_T : pint.Quantity
           The temperature difference across the air cooler.
       air_cooler_fan_eff : pint.Quantity
           The efficiency of the air cooler fan.
       air_cooler_press_drop : pint.Quantity
           The pressure drop across the air cooler.
       water_press : pint.Quantity
           The water pressure associated with the air cooler pressure drop.
       eta_compressor : pint.Quantity
           The efficiency of the compressor in the demethanizer process.
       prime_mover_type : str
           The type of prime mover used in the process.

    Methods
       run(analysis)
           Simulates the Demethanizer process to separate the incoming gas stream
           into a methane-rich stream and a heavier hydrocarbon stream.
   """

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        # TODO: avoid process names in contents.
        self._required_inputs = [
            "gas for demethanizer"
        ]

        self._required_outputs = [
            "gas for gas partition",
            "gas for NGL",
        ]

        field = self.field
        self.demethanizer_tbl = field.model.demethanizer
        self.mol_per_scf = field.model.const("mol-per-scf")

        self.air_cooler_delta_T = None
        self.air_cooler_fan_eff = None
        self.air_cooler_press_drop = None
        self.air_cooler_speed_reducer_eff = None
        self.column_pressure = None
        self.eta_compressor = None
        self.eta_reboiler_demethanizer = None
        self.feed_press_demethanizer = None
        self.methane_to_LPG_ratio = None
        self.prime_mover_type = None
        self.water_press = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field
        self.feed_press_demethanizer = self.attr("feed_press_demethanizer")
        self.column_pressure = self.attr("column_pressure")
        self.methane_to_LPG_ratio = self.attr("methane_to_LPG_ratio")
        self.eta_reboiler_demethanizer = self.attr("eta_reboiler_demethanizer")
        self.air_cooler_speed_reducer_eff = self.attr("air_cooler_speed_reducer_eff")
        self.air_cooler_delta_T = self.attr("air_cooler_delta_T")
        self.air_cooler_fan_eff = self.attr("air_cooler_fan_eff")
        self.air_cooler_press_drop = self.attr("air_cooler_press_drop")
        self.water_press = (field.water.density() *
                           self.air_cooler_press_drop *
                           field.model.const("gravitational-acceleration"))
        self.eta_compressor = self.attr("eta_compressor")
        self.prime_mover_type = self.attr("prime_mover_type")

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        # mass rate
        input = self.find_input_stream("gas for demethanizer")
        processing_unit_loss_rate_df = field.get_process_data("processing_unit_loss_rate_df")
        if input.is_uninitialized() or  processing_unit_loss_rate_df is None:
            return

        loss_rate = processing_unit_loss_rate_df.T[self.name].values[0]
        gas_fugitives = self.set_gas_fugitives(input, loss_rate)

        # Demethanizer modeling based on Aspen HYSYS
        # Input values for variable getting from HYSYS
        variable_bound_dict = {"feed_gas_press": [600.0, 1000.0],  # unit in psia
                               "column_press": [155.0, 325.0],  # unit in psia
                               "methane_to_LPG_ratio": [0.01, 0.05],
                               "inlet_C1_mol_frac": [0.50, 0.95],
                               "inlet_C2_mol_frac": [0.05, 0.95]}
        feed_gas_press =\
            get_bounded_value(self.feed_press_demethanizer.to("psia").m, "feed_gas_press", variable_bound_dict)
        column_press =\
            get_bounded_value(self.column_pressure.to("psia").m, "column_press", variable_bound_dict)
        methane_to_LPG_ratio =\
            get_bounded_value(self.methane_to_LPG_ratio.to("frac").m, "methane_to_LPG_ratio", variable_bound_dict)

        feed_gas_mol_frac = self.gas.component_molar_fractions(input)

        if "C1" not in feed_gas_mol_frac.index:
            _logger.warning(f"Feed gas does not contain C1")
            inlet_C1_mol_frac = 0
        else:
            inlet_C1_mol_frac =\
                get_bounded_value(feed_gas_mol_frac["C1"].to("frac").m, "inlet_C1_mol_frac", variable_bound_dict)

        if "C2" not in feed_gas_mol_frac.index:
            _logger.warning(f"Feed gas does not contain C2")
            inlet_C2_mol_frac = 0
        else:
            inlet_C2_mol_frac =\
                get_bounded_value(feed_gas_mol_frac["C2"].to("frac").m, "inlet_C2_mol_frac", variable_bound_dict)

        gas_volume_rate = self.gas.volume_flow_rate_STP(input)

        # Multiplier for gas load in correlation equation
        multiplier = 99.8
        scale_value = gas_volume_rate.to("mmscf/day").m / multiplier

        x1 = feed_gas_press
        x2 = column_press
        x3 = methane_to_LPG_ratio
        x4 = inlet_C1_mol_frac
        x5 = inlet_C2_mol_frac
        corr_result_df = run_corr_eqns(x1, x2, x3, x4, x5, self.demethanizer_tbl)
        reboiler_heavy_duty = ureg.Quantity(max(0., corr_result_df.loc["Reboiler", :].sum() * scale_value), "kW")
        cooler_thermal_load = ureg.Quantity(max(0., corr_result_df.loc["HEX", :].sum() * scale_value), "kW")
        NGL_label = ["NGL C1", "NGL C2", "NGL C3", "NGL C4"]
        fuel_gas_label = ["fuel gas C1", "fuel gas C2", "fuel gas C3", "fuel gas C4"]
        hydrocarbon_label = ["C1", "C2", "C3", "C4"]
        NGL_mol_frac = pd.Series({name: max(0, corr_result_df.loc[tbl_name, :].sum()) for name, tbl_name in
                                  zip(hydrocarbon_label, NGL_label)},
                                 dtype="pint[frac]")
        fuel_gas_mol_frac = pd.Series({name: max(0, corr_result_df.loc[tbl_name, :].sum()) for name, tbl_name in
                                       zip(hydrocarbon_label, fuel_gas_label)},
                                      dtype="pint[frac]")

        gas_volume_rates = field.gas.volume_flow_rates_STP(input)

        if NGL_mol_frac["C2"].m == 0 or (
                fuel_gas_mol_frac["C1"] - NGL_mol_frac["C1"] * fuel_gas_mol_frac["C2"] / NGL_mol_frac["C2"]).m == 0:
            fuel_gas_prod = ureg.Quantity(0, "mole/day")
        else:
            fuel_gas_prod = \
                (gas_volume_rates["C1"] - NGL_mol_frac["C1"] / NGL_mol_frac["C2"] * gas_volume_rates["C2"]) / \
                (fuel_gas_mol_frac["C1"] - NGL_mol_frac["C1"] * fuel_gas_mol_frac["C2"] / NGL_mol_frac["C2"])

        reboiler_fuel_use = reboiler_heavy_duty * self.eta_reboiler_demethanizer
        cooler_energy_consumption = predict_blower_energy_use(self, cooler_thermal_load)

        fuel_gas_volume_rate = fuel_gas_prod * field.gas.component_mass_fractions(fuel_gas_mol_frac)
        fuel_gas_mass = fuel_gas_volume_rate * field.gas.component_gas_rho_STP[fuel_gas_volume_rate.index]

        gas_to_partition = self.find_output_stream("gas for gas partition")
        gas_to_partition.copy_flow_rates_from(input)
        gas_to_partition.subtract_rates_from(gas_fugitives)
        gas_to_partition.set_rates_from_series(fuel_gas_mass, PHASE_GAS, upper_bound_stream=input)

        gas_to_LPG = self.find_output_stream("gas for NGL")
        gas_to_LPG.copy_flow_rates_from(input)
        gas_to_LPG.tp.set(T=STP.T)
        gas_to_LPG.subtract_rates_from(gas_to_partition)

        self.set_iteration_value(gas_to_partition.total_flow_rate() + gas_to_LPG.total_flow_rate())

        # TODO: ethane to petrochemicals

        input_tp = input.tp

        # inlet boosting compressor
        inlet_compressor_energy_consump, _, _ = \
            Compressor.get_compressor_energy_consumption(field,
                                                         self.prime_mover_type,
                                                         self.eta_compressor,
                                                         self.feed_press_demethanizer / input_tp.P,
                                                         input,
                                                         inlet_tp=input.tp)

        # outlet compressor
        fuel_gas_exit_press = ureg.Quantity(corr_result_df.loc["fuel gas pressure", :].sum(), "psia")
        fuel_gas_stream = Stream("fuel_gas", tp=TemperaturePressure(input_tp.T, fuel_gas_exit_press))
        fuel_gas_stream.set_rates_from_series(fuel_gas_mass, PHASE_GAS, upper_bound_stream=input)

        outlet_compressor_energy_consump, _, _ = \
            Compressor.get_compressor_energy_consumption(field,
                                                         self.prime_mover_type,
                                                         self.eta_compressor,
                                                         input_tp.P / fuel_gas_exit_press,
                                                         fuel_gas_stream)

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier,
                            inlet_compressor_energy_consump + outlet_compressor_energy_consump + reboiler_fuel_use)
        energy_use.set_rate(EN_ELECTRICITY, cooler_energy_consumption)

        # import/export
        self.set_import_from_energy(energy_use)

        # emissions
        self.set_combustion_emissions()
        self.emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
