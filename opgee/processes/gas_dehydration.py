#
# GasDehydration class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import numpy as np

from .shared import get_bounded_value, predict_blower_energy_use
from .. import ureg
from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY
from ..error import OpgeeException
from ..log import getLogger
from ..process import Process
from ..process import run_corr_eqns
from ..thermodynamics import ChemicalInfo

_logger = getLogger(__name__)


class GasDehydration(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        model = field.model

        self.gas = field.gas
        self.gas_dehydration_tbl = model.gas_dehydration_tbl
        self.mol_to_scf = model.const("mol-per-scf")
        self.air_elevation_const = model.const("air-elevation-corr")
        self.air_density_ratio = model.const("air-density-ratio")
        self.reflux_ratio = field.reflux_ratio
        self.regeneration_feed_temp = field.regeneration_feed_temp
        self.eta_reboiler_dehydrator = self.attr("eta_reboiler_dehydrator")
        self.air_cooler_delta_T = self.attr("air_cooler_delta_T")
        self.air_cooler_press_drop = self.attr("air_cooler_press_drop")
        self.air_cooler_fan_eff = self.attr("air_cooler_fan_eff")
        self.air_cooler_speed_reducer_eff = self.attr("air_cooler_speed_reducer_eff")

        self.water_press = field.water.density() * \
                           self.air_cooler_press_drop * \
                           field.model.const("gravitational-acceleration")

        self.gas_path = field.gas_path

        self.gas_path_dict = {"Minimal": "gas for gas partition",
                              "Acid Gas": "gas for AGR",
                              "Acid Wet Gas": "gas for AGR",
                              "CO2-EOR Membrane": "gas for chiller",
                              "CO2-EOR Ryan Holmes": "gas for Ryan Holmes",
                              "Sour Gas Reinjection": "gas for sour gas compressor",
                              "Wet Gas": "gas for demethanizer"}

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        # mass rate
        input = self.find_input_stream("gas for gas dehydration")
        processing_unit_loss_rate_df = field.get_process_data("processing_unit_loss_rate_df")
        if input.is_uninitialized() or processing_unit_loss_rate_df is None:
            return

        loss_rate = processing_unit_loss_rate_df.T[self.name].values[0]
        gas_fugitives = self.set_gas_fugitives(input, loss_rate)

        try:
            output = self.gas_path_dict[self.gas_path]
        except:
            raise OpgeeException(f"{self.name} gas path is not recognized:{self.gas_path}. "
                                 f"Must be one of {list(self.gas_path_dict.keys())}")

        output_gas = self.find_output_stream(output)
        output_gas.copy_flow_rates_from(input)
        output_gas.subtract_rates_from(gas_fugitives)

        self.set_iteration_value(output_gas.total_flow_rate())

        feed_gas_temp, feed_gas_press = input.tp.get()

        # how much moisture in gas (Bukacek Method) [Carrioll JJ. The water content of acid gas and sour gas from
        # 100°F to 220°F and pressures to 10000 psia, Paper presented at the 81st Annual Gas Processors Association
        # Convention, 11–13 March 2002, Dallas, Texas, USA.] TODO: Bukacek method is incorrect when NG is sour.
        #  Considering using a different method to calculate water content
        water_critical_temp = self.gas.component_Tc["H2O"]
        water_critical_press = self.gas.component_Pc["H2O"]
        tau = ureg.Quantity(1 - feed_gas_temp.to("kelvin").m / water_critical_temp.to("kelvin").m, "dimensionless")
        Tc_over_T = ureg.Quantity(water_critical_temp.to("kelvin").m / feed_gas_temp.to("kelvin").m, "dimensionless")
        pseudo_pressure = self.pseudo_pressure(tau, Tc_over_T, water_critical_press)
        B = 10 ** (6.69449 - 3083.87 / feed_gas_temp.to("degR").m)
        water_content = 47430 * pseudo_pressure.to("Pa").m / feed_gas_press.to("Pa").m + B
        water_content = ureg.Quantity(water_content, "lb/mmscf")

        gas_volume_rate = self.gas.volume_flow_rate_STP(input)
        gas_multiplier = gas_volume_rate.to("mmscf/day").m / 1.0897  # multiplier for gas load in correlation equation
        water_content_volume = water_content * gas_volume_rate / ChemicalInfo.mol_weight("H2O") / self.mol_to_scf
        water_content_volume = water_content_volume / gas_multiplier

        # Gas dehydration modeling based on Aspen HYSYS
        # Input values for variable getting from HYSYS
        variable_bound_dict = {"feed_gas_press": [14.7, 1014.7],  # unit in psia
                               "feed_gas_temp": [80.0, 100.0],  # unit in degree F
                               "water_content_volume": [0.0005, 0.005],
                               "reflux_ratio": [1.5, 3.0],
                               "regeneration_feed_temp": [190.0, 200.0]}  # unit in degree F

        x1 = get_bounded_value(feed_gas_press.to("psia").m, "feed_gas_press", variable_bound_dict)
        x2 = get_bounded_value(feed_gas_temp.to("degF").m, "feed_gas_temp", variable_bound_dict)
        x3 = get_bounded_value(water_content_volume.to("mmscf/day").m, "water_content_volume", variable_bound_dict)
        x4 = get_bounded_value(self.reflux_ratio.m, "reflux_ratio", variable_bound_dict)
        x5 = get_bounded_value(self.regeneration_feed_temp.to("degF").m, "regeneration_feed_temp", variable_bound_dict)

        corr_result_df = run_corr_eqns(x1, x2, x3, x4, x5, self.gas_dehydration_tbl)
        reboiler_heavy_duty = ureg.Quantity(max(0., corr_result_df["Reboiler"] * gas_multiplier), "kW")
        pump_duty = ureg.Quantity(max(0, corr_result_df["Pump"] * gas_multiplier), "kW")
        condenser_thermal_load = ureg.Quantity(max(0., corr_result_df["Condenser"] * gas_multiplier), "kW")

        # TODO: Add this stream to water treatment process
        water_output = ureg.Quantity(max(0., corr_result_df["Resid water"]), "lb/mmscf")

        reboiler_fuel_use = reboiler_heavy_duty * self.eta_reboiler_dehydrator
        air_cooler_energy_consumption = predict_blower_energy_use(self, condenser_thermal_load)

        # energy-use
        energy_use = self.energy
        energy_use.set_rate(EN_NATURAL_GAS, reboiler_fuel_use)
        energy_use.set_rate(EN_ELECTRICITY, air_cooler_energy_consumption + pump_duty)

        # import/export
        self.set_import_from_energy(energy_use)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)

        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)

    @staticmethod
    def pseudo_pressure(tau, Tc_over_T, critical_pressure):
        """

        :param Tc_over_T:
        :param tau:
        :param critical_pressure: water critical pressure (unit = "Pa")
        :return: (flaot) pseudo pressure (unit = "Pa")
        """

        a1 = -7.85951783
        a2 = 1.84408259
        a3 = -11.7866497
        a4 = 22.6807411
        a5 = -15.9618719
        a6 = 1.80122502

        tau = tau.m
        Tc_over_T = Tc_over_T.m
        critical_pressure = critical_pressure.m

        Pv_over_Pc = np.exp((a1 * tau +
                             a2 * tau ** 1.5 +
                             a3 * tau ** 3 +
                             a4 * tau ** 3.5 +
                             a5 * tau ** 4 +
                             a6 * tau ** 7.5) * Tc_over_T)
        result = Pv_over_Pc * critical_pressure
        return ureg.Quantity(result, "Pa")
