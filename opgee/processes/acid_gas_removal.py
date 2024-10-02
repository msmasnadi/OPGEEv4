#
# AcidGasRemoval class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .. import ureg
from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..energy import EN_ELECTRICITY
from ..log import getLogger
from ..process import Process, run_corr_eqns
from .compressor import Compressor
from .shared import get_energy_carrier, predict_blower_energy_use, get_bounded_value, get_energy_consumption

_logger = getLogger(__name__)

amine_solution_K_value_dict = { "conv DEA" : 1.45,
                                "high DEA": 0.95,
                                "MEA" : 2.05,
                                "DGA" : 1.28,
                                "MDEA" : 1.25}


class AcidGasRemoval(Process):
    """
    A process class that removes acid gases (CO2 and H2S) from a natural gas stream.

    Inputs:
       - gas for AGR: Gas stream containing CO2 and H2S to be removed.

    Outputs:
       - gas for demethanizer: Gas stream with CO2 and H2S removed, and fed to the demethanizer.
       - gas for CO2 compressor: Gas stream containing CO2 to be compressed and injected back into the reservoir.

    Attributes:
       - type_amine: The type of amine solution used for CO2 and H2S removal.
       - ratio_reflux_reboiler: The reflux-to-reboil ratio used in the process.
       - AGR_feedin_press: The feed-in pressure of the gas stream.
       - regeneration_temp: The temperature at which the amine solution is regenerated.
       - eta_reboiler: The efficiency of the reboiler in the process.
       - air_cooler_delta_T: The temperature difference across the air cooler.
       - air_cooler_press_drop: The pressure drop across the air cooler.
       - air_elevation_const: A constant used to calculate the air density ratio.
       - air_density_ratio: The ratio of air density at the air cooler elevation to sea level density.
       - water_press: The pressure drop across the air cooler due to water vapor.
       - air_cooler_fan_eff: The efficiency of the air cooler fan.
       - air_cooler_speed_reducer_eff: The efficiency of the air cooler speed reducer.
       - AGR_table: A lookup table for AGR calculations.
       - eta_compressor: The efficiency of the CO2 compressor.
       - prime_mover_type: The type of prime mover used in the process.
       - amine_solution_K_value: The K value of the amine solution used for CO2 and H2S removal.

    Methods:
       - run(analysis): Runs the acid gas removal process.
       - calculate_energy_consumption_from_Aspen(input_stream, output_stream, mol_frac_CO2, mol_frac_H2S): Calculates energy
         consumption for the acid gas removal process using Aspen HYSYS simulation.
       - calculate_energy_consumption_from_textbook(input_stream, mol_frac_CO2, mol_frac_H2S): Calculates energy consumption
         for the acid gas removal process using a textbook method.
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self._required_inputs = [
            "gas for AGR",          # TODO: avoid process names in contents. Should be "acidic gas"?
        ]

        self._required_outputs = [
            # TODO: If the process name were avoided, we could have just one output stream
            #  with, say, "deacidified gas". Should describe the contents, not the destination.
            # One of these must exist.
            ("gas for demethanizer",  # TODO: avoid process names in contents
             "gas for gas partition") # TODO: avoid process names in contents
        ]

        # Optional streams include:
        # "gas for CO2 compressor" (output)

        self.AGR_feedin_press = None
        self.AGR_table = None
        self.air_cooler_delta_T = None
        self.air_cooler_fan_eff = None
        self.air_cooler_press_drop = None
        self.air_cooler_speed_reducer_eff = None
        self.air_density_ratio = None
        self.air_elevation_const = None
        self.amine_solution_K_value = None
        self.eta_compressor = None
        self.eta_reboiler = None
        self.gas_comp_H2S = None
        self.prime_mover_type = None
        self.ratio_reflux_reboiler = None
        self.regeneration_temp = None
        self.type_amine = None
        self.type_amine = None
        self.water_press = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field
        m = field.model

        self.type_amine = self.attr("type_amine")
        self.ratio_reflux_reboiler = self.attr("ratio_reflux_reboiler")

        self.gas_comp_H2S = field.attr("gas_comp_H2S")

        # TODO: Add this to smart default mode
        if self.gas_comp_H2S < ureg.Quantity(1, "percent"):
            self.type_amine = "conv DEA"
        else:
            self.type_amine = "MDEA"
            self.ratio_reflux_reboiler = ureg.Quantity(7.0, "frac")

        self.AGR_feedin_press = field.AGR_feedin_press
        self.regeneration_temp = self.attr("regeneration_temp")
        self.eta_reboiler = self.attr("eta_reboiler")
        self.air_cooler_delta_T = self.attr("air_cooler_delta_T")
        self.air_cooler_press_drop = self.attr("air_cooler_press_drop")
        self.air_elevation_const = m.const("air-elevation-corr")
        self.air_density_ratio = m.const("air-density-ratio")
        self.water_press = (field.water.density() * self.air_cooler_press_drop *
                            m.const("gravitational-acceleration"))
        self.air_cooler_fan_eff = self.attr("air_cooler_fan_eff")
        self.air_cooler_speed_reducer_eff = self.attr("air_cooler_speed_reducer_eff")
        self.AGR_table = m.AGR_tbl
        self.eta_compressor = self.attr("eta_compressor")
        self.prime_mover_type = self.attr("prime_mover_type")

        value = amine_solution_K_value_dict[self.type_amine] * 100
        self.amine_solution_K_value = ureg.Quantity(value, "gallon*day/minutes/mmscf")

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        if not self.all_streams_ready("gas for AGR"):
            return

        # Calculate mass rate
        gas_input_stream = self.find_input_streams("gas for AGR", combine=True)
        processing_unit_loss_rate_df = field.get_process_data("processing_unit_loss_rate_df")
        if gas_input_stream.is_uninitialized() or processing_unit_loss_rate_df is None:
            return

        loss_rate = processing_unit_loss_rate_df.T[self.name].values[0]
        gas_fugitives = self.set_gas_fugitives(gas_input_stream, loss_rate)

        CO2_feed_mass_rate = gas_input_stream.gas_flow_rate("CO2")
        CH4_feed_mass_rate = gas_input_stream.gas_flow_rate("C1")
        H2S_feed_mass_rate = gas_input_stream.gas_flow_rate("H2S")
        CO2_to_demethanizer = min(0.05 * CO2_feed_mass_rate, 0.001 * CH4_feed_mass_rate)
        H2S_to_demethanizer = ureg.Quantity(0.0, "tonne/day")

        # Calculate output stream for demethanizer
        output_gas = self.find_output_stream("gas for demethanizer", raiseError=False) or \
                     self.find_output_stream("gas for gas partition")
        output_gas.copy_flow_rates_from(gas_input_stream)
        output_gas.set_gas_flow_rate("CO2", CO2_to_demethanizer)
        if field.gas_path != "CO2-EOR Membrane":
            H2S_to_demethanizer = 0.05 * gas_input_stream.gas_flow_rate("H2S")
            output_gas.set_gas_flow_rate("H2S", H2S_to_demethanizer)
        output_gas.subtract_rates_from(gas_fugitives)
        self.set_iteration_value(output_gas.total_flow_rate())

        gas_to_CO2_reinjection = self.find_output_stream("gas for CO2 compressor", raiseError=False)
        if gas_to_CO2_reinjection is not None:
            gas_to_CO2_reinjection.copy_flow_rates_from(gas_input_stream)
            gas_to_CO2_reinjection.subtract_rates_from(output_gas)
            gas_to_CO2_reinjection.subtract_rates_from(gas_fugitives)
        else:
            CO2_fugitive_mass_rate = CO2_feed_mass_rate - CO2_to_demethanizer
            H2S_fugitve_mass_rate = H2S_feed_mass_rate - H2S_to_demethanizer
            gas_fugitives.set_gas_flow_rate("CO2", CO2_fugitive_mass_rate)
            gas_fugitives.set_gas_flow_rate("H2S", H2S_fugitve_mass_rate)

        feed_gas_mol_frac = self.gas.component_molar_fractions(gas_input_stream)
        mol_frac_H2S = feed_gas_mol_frac["H2S"] if "H2S" in feed_gas_mol_frac else ureg.Quantity(0, "frac")
        mol_frac_CO2 = feed_gas_mol_frac["CO2"] if "CO2" in feed_gas_mol_frac else ureg.Quantity(0, "frac")

        if mol_frac_H2S.m == 0.0 and mol_frac_CO2 == 0.0:
            _logger.warning(f"Feed gas does not contain H2S and CO2, please consider using non-AGR gas processing path")
            return

        if mol_frac_H2S.m <= 0.15 and mol_frac_CO2 <= 0.2:
            compressor_energy_consumption, reboiler_fuel_use, electricity_consump =\
                self.calculate_energy_consumption_from_Aspen(gas_input_stream, output_gas, mol_frac_CO2, mol_frac_H2S)
        else:
            compressor_energy_consumption, reboiler_fuel_use, electricity_consump = \
                self.calculate_energy_consumption_from_textbook(gas_input_stream, mol_frac_CO2, mol_frac_H2S)

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, compressor_energy_consumption + reboiler_fuel_use)
        energy_use.add_rate(EN_ELECTRICITY, electricity_consump) \
            if energy_carrier == EN_ELECTRICITY else energy_use.set_rate(EN_ELECTRICITY, electricity_consump)

        # import and export
        self.set_import_from_energy(energy_use)

        # emissions
        combustion_emission = self.compute_emission_combustion()
        self.emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)
        self.emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)


    def calculate_energy_consumption_from_Aspen(self, input, output_gas, mol_frac_CO2, mol_frac_H2S):
        """
        Calculates the energy consumption in the AGR gas processing unit using Aspen simulation.

        :param input: (Stream) Input gas stream
        :param output_gas: (Stream) Output gas stream
        :param mol_frac_CO2: (Quantity) Molar fraction of CO2 in the input gas stream
        :param mol_frac_H2S: (Quantity) Molar fraction of H2S in the input gas stream
        :return: (tuple) Compressor energy consumption (Quantity), Reboiler fuel use (Quantity), and
            Electricity consumption (Quantity)
        """

        # Define a dictionary of the bounds for each variable used in the calculation from HYSYS
        variable_bound_dict = {"mol_frac_CO2": [0.0, 0.2],
                               "mol_frac_H2S": [0.0, 0.15],
                               "reflux_ratio": [1.5, 3.0],
                               "regen_temp": [190.0, 220.0],  # unit in degree F
                               "feed_gas_press": [14.7, 514.7]}  # unit in psia

        # Bound the values for mol_frac_CO2 and mol_frac_H2S using the defined bounds
        mol_frac_CO2 = get_bounded_value(mol_frac_CO2.to("frac").m, "mol_frac_CO2", variable_bound_dict)
        mol_frac_H2S = get_bounded_value(mol_frac_H2S.to("frac").m, "mol_frac_H2S", variable_bound_dict)

        # Set the type of amine based on the mol_frac_H2S value
        if self.type_amine == "MDEA":
            variable_bound_dict["reflux_ratio"] = [6.5, 8.0]

        # Bound the values for reflux_ratio, regen_temp, and feed_gas_press using the defined bounds
        reflux_ratio = get_bounded_value(self.ratio_reflux_reboiler.to("frac").m, "reflux_ratio", variable_bound_dict)
        regen_temp = get_bounded_value(self.regeneration_temp.to("degF").m, "regen_temp", variable_bound_dict)
        feed_gas_press = get_bounded_value(self.AGR_feedin_press.to("psia").m, "feed_gas_press", variable_bound_dict)

        # Calculate the gas volume rate and the gas multiplier used in the correlation equation
        gas_volume_rate = self.gas.volume_flow_rate_STP(input)
        gas_multiplier = gas_volume_rate.to("mmscf/day").m / 1.0897  # multiplier for gas load in correlation equation

        # Set the input variables for the correlation equation
        x1 = mol_frac_CO2
        x2 = mol_frac_H2S
        x3 = reflux_ratio
        x4 = regen_temp
        x5 = feed_gas_press

        # Run the correlation equation to get the reboiler, condenser, and cooler thermal loads
        corr_result_df = run_corr_eqns(x1, x2, x3, x4, x5, self.AGR_table.loc[:, self.type_amine])
        reboiler_heavy_duty = ureg.Quantity(max(0.0, corr_result_df["Reboiler"] * gas_multiplier), "kW")
        condenser_thermal_load = ureg.Quantity(max(0.0, corr_result_df["Condenser"] * gas_multiplier), "kW")
        cooler_thermal_load = ureg.Quantity(max(0.0, corr_result_df["Cooler"] * gas_multiplier), "kW")

        reboiler_fuel_use = reboiler_heavy_duty * self.eta_reboiler
        pump_duty_elec = ureg.Quantity(max(0.0, corr_result_df["Pump"] * gas_multiplier), "kW")
        condenser_elec_consumption = predict_blower_energy_use(self, condenser_thermal_load)
        amine_cooler_elec_consumption = predict_blower_energy_use(self, cooler_thermal_load)

        # Calculate the reboiler fuel use
        overall_compression_ratio = ureg.Quantity(feed_gas_press, "psia") / input.tp.P
        compressor_energy_consumption, temp, _ = \
            Compressor.get_compressor_energy_consumption(self.field,
                                                         self.prime_mover_type,
                                                         self.eta_compressor,
                                                         overall_compression_ratio,
                                                         output_gas,
                                                         inlet_tp=input.tp)

        electricity_consump = pump_duty_elec + condenser_elec_consumption + amine_cooler_elec_consumption
        return compressor_energy_consumption, reboiler_fuel_use, electricity_consump

    def calculate_energy_consumption_from_textbook(self, input, mol_frac_CO2, mol_frac_H2S):
        """
            Calculate energy consumption for the amine unit using the textbook method.

            :param input: Stream object, input stream to the amine unit.
            :param mol_frac_CO2: (Quantity) Molar fraction of CO2 in the input gas stream
            :param mol_frac_H2S: (Quantity) Molar fraction of H2S in the input gas stream
            :return: (tuple) Compressor energy consumption (Quantity) == 0, Reboiler fuel use (Quantity), and
                        Electricity consumption (Quantity)
        """

        # Calculate feed gas volume rate at STP
        feedin_gas_volume_rate_STP = self.gas.volume_flow_rates_STP(input)

        # Calculate CO2 and H2S volume rate, if not present set it to 0
        CO2_volume_rate =\
            feedin_gas_volume_rate_STP["CO2"] if mol_frac_CO2.m != 0 else ureg.Quantity(0, "mmscf/day")
        H2S_volume_rate =\
            feedin_gas_volume_rate_STP["H2S"] if mol_frac_H2S.m != 0 else ureg.Quantity(0, "mmscf/day")
        amine_circulation_rate = self.amine_solution_K_value * (CO2_volume_rate + H2S_volume_rate)

        # Pumps energy consumption
        circulation_pump_HP =\
            ureg.Quantity(amine_circulation_rate.to("gallon / minute").m * (input.tp.P.m + 50) * 0.00065, "horsepower")
        booster_pump_HP = ureg.Quantity(amine_circulation_rate.to("gallon / minute").m * 0.06, "horsepower")
        reflux_pump_HP = booster_pump_HP
        total_pump_HP = circulation_pump_HP + booster_pump_HP + reflux_pump_HP
        total_pump_energy_consump = get_energy_consumption("Electric_motor", total_pump_HP)

        # Air coolers energy consumption
        amine_cooler_HP = ureg.Quantity(amine_circulation_rate.to("gallon / minute").m * 0.36, "horsepower")
        reflux_condenser_HP = amine_cooler_HP * 2
        total_cooling_HP = amine_cooler_HP + reflux_condenser_HP
        total_coolers_energy_consump = get_energy_consumption("Electric_motor", total_cooling_HP)

        # Reboiler energy consumption
        reboiler_heat_duty = amine_circulation_rate * ureg.Quantity(72000, "btu*minute/gallon/hr") * 1.15
        total_reboiler_erergy_consump = self.eta_reboiler * reboiler_heat_duty

        return ureg.Quantity(0, "mmbtu/day"), total_reboiler_erergy_consump, total_coolers_energy_consump + total_pump_energy_consump






