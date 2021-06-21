from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID
from opgee import ureg
from ..emissions import EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES
from ..energy import Energy, EN_NATURAL_GAS, EN_ELECTRICITY

_logger = getLogger(__name__)


class CrudeOilDewatering(Process):
    # For our initial, highly-simplified test case, we just shuttle the oil and water
    # to two output streams and force the temperature and pressure to what was in the
    # OPGEE v3 workbook for the default field.
    def run(self, analysis):
        self.print_running_msg()

        field = self.get_field()

        heater_treater = field.attr("heater_treater")
        temperature_heater_treater = self.attr("temperature_heater_treater")
        heat_loss = self.attr("heat_loss")
        prime_mover_type = self.attr("prime_mover_type")
        eta_gas = (self.attr("eta_gas")).to("frac")
        eta_electricity = (self.attr("eta_electricity")).to("frac")

        # mass rate
        input = self.find_input_stream("crude oil")
        temperature = input.temperature
        pressure = input.pressure
        oil_rate = input.flow_rate("oil", PHASE_LIQUID)
        water_rate = input.flow_rate("H2O", PHASE_LIQUID)

        oil_to_stabilization = self.find_output_stream("crude oil")
        # Check

        oil_to_stabilization.set_liquid_flow_rate("oil", oil_rate)
        temp = temperature_heater_treater if heater_treater else temperature
        oil_to_stabilization.set_temperature_and_pressure(temp, pressure)

        water_to_stabilization = self.find_output_stream("water")
        # Check
        self.set_iteration_value((oil_to_stabilization.total_flow_rate(),
                                  water_to_stabilization.total_flow_rate()))
        water_to_stabilization.set_liquid_flow_rate("H2O", water_rate)
        water_to_stabilization.set_temperature_and_pressure(temp, pressure)

        # dewater heater/treater
        average_oil_temp = ureg.Quantity((temperature.m+temperature_heater_treater.m)/2, "degF")
        oil_heat_capacity = field.oil.specific_heat(field.oil.API, average_oil_temp)
        water_heat_capacity = field.water.specific_heat(average_oil_temp)
        delta_temp = ureg.Quantity(temperature_heater_treater.m - temperature.m, "delta_degF")
        heat_duty = ureg.Quantity(0, "mmBtu/day")
        if heater_treater:
            eff = (1 + heat_loss.to("frac")).to("frac")
            heat_duty = ((oil_rate * oil_heat_capacity + water_rate * water_heat_capacity) *
                         delta_temp * eff).to("mmBtu/day")

        # energy_use
        energy_use = self.energy
        energy_carrier = EN_NATURAL_GAS if prime_mover_type == "NG_engine" else EN_ELECTRICITY
        energy_consumption = heat_duty / eta_gas if prime_mover_type == "NG_engine" else heat_duty / eta_electricity
        energy_use.set_rate(energy_carrier, energy_consumption.to("mmBtu/day"))

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        process_EF = self.get_process_EF()
        combusion_emission = (energy_for_combustion * process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "GHG", combusion_emission)