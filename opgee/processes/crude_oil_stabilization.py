import numpy as np

from ..log import getLogger
from ..process import Process
from ..stream import Stream, PHASE_LIQUID, PHASE_GAS
from opgee import ureg
from ..energy import Energy, EN_NATURAL_GAS, EN_ELECTRICITY
from ..compressor import Compressor
from ..emissions import EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES
from .shared import get_energy_carrier

_logger = getLogger(__name__)


class CrudeOilStabilization(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.stab_temp = self.attr("stab_temp")
        self.stab_press = self.attr("stab_press")
        self.mol_per_scf = field.model.const("mol-per-scf")
        self.stab_gas_press = field.attr("gas_pressure_after_boosting")
        self.eps_stab = self.attr("eps_stab")
        self.eta_gas = self.attr("eta_gas")
        self.eta_electricity = self.attr("eta_electricity")
        self.prime_mover_type = self.attr("prime_mover_type")
        self.compressor_eff = field.attr("eta_compressor")      # TODO: why the name change? Other vars are eta_XXX.

    def run(self, analysis):
        self.print_running_msg()

        # TODO: Wennan, this builds in a "hidden" dependency and surprising alteration
        # TODO: the model without alerting the user. Is this the best way to handle this?
        if self.field.attr("crude_oil_dewatering_output") != self.name:
            self.enabled = False
            return

        # mass rate
        input = self.find_input_stream("oil for stabilization")
        if input.is_empty():
            return
        average_temp = (self.stab_temp.m + input.temperature.m) / 2
        average_temp = ureg.Quantity(average_temp, "degF")

        oil = self.field.oil
        oil_specific_heat = oil.specific_heat(oil.API, average_temp)
        stream = Stream("out_stream", temperature=self.stab_temp, pressure=self.stab_press)
        solution_GOR_inlet = oil.solution_gas_oil_ratio(input,
                                                        oil.oil_specific_gravity,
                                                        oil.gas_specific_gravity,
                                                        oil.gas_oil_ratio)
        solution_GOR_outlet = oil.solution_gas_oil_ratio(stream,
                                                         oil.oil_specific_gravity,
                                                         oil.gas_specific_gravity,
                                                         oil.gas_oil_ratio)
        oil_mass_rate = input.flow_rate("oil", PHASE_LIQUID)
        oil_density = oil.density(input,
                                  oil.oil_specific_gravity,
                                  oil.gas_specific_gravity,
                                  oil.gas_oil_ratio)
        gas_removed_by_stabilizer = oil_mass_rate * (solution_GOR_inlet - solution_GOR_outlet) / oil_density
        gas_removed_molar_rate = gas_removed_by_stabilizer * self.mol_per_scf * oil.gas_comp  # Pandas Series
        gas_removed_mass_rate = oil.component_MW[gas_removed_molar_rate.index] * gas_removed_molar_rate

        output_stab_gas = self.find_output_stream("gas for gas gathering")
        output_stab_gas.set_temperature_and_pressure(self.stab_temp, self.stab_gas_press)
        output_stab_gas.set_rates_from_series(gas_removed_mass_rate, PHASE_GAS)

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)

        output = self.find_output_stream("oil for storage")
        oil_for_storage = oil_mass_rate - output_stab_gas.total_gas_rate() - gas_fugitives.total_gas_rate()
        output.set_liquid_flow_rate("oil", oil_for_storage, t=self.stab_temp, p=input.pressure)

        # energy use
        heat_duty = oil_mass_rate * oil_specific_heat * (self.stab_temp - input.temperature) * (1 + self.eps_stab)
        energy_use = self.energy

        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_consumption = heat_duty / self.eta_gas if self.prime_mover_type == "NG_engine" else heat_duty / self.eta_electricity

        # boosting compressor for stabilizer
        overall_compression_ratio = self.stab_gas_press / input.pressure
        compression_ratio_per_stage = Compressor.get_compression_ratio(overall_compression_ratio)
        num_of_compression = Compressor.get_num_of_compression(overall_compression_ratio)
        work_sum, _ = Compressor.get_compressor_work_temp(self.field, input.temperature, input.pressure,
                                                       output_stab_gas, compression_ratio_per_stage, num_of_compression)
        horsepower = work_sum * gas_removed_by_stabilizer
        brake_horsepower = horsepower / self.compressor_eff
        energy_consumption += self.get_energy_consumption(self.prime_mover_type, brake_horsepower)
        energy_use.set_rate(energy_carrier, energy_consumption.to("mmBtu/day"))

        # emission rate
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "CO2", combustion_emission)

        emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)

        self.field.save_process_data(oil_stab_solution_GOR_outlet=solution_GOR_outlet)
