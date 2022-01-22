from .. import ureg
from ..emissions import EM_COMBUSTION
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY
from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID
from ..error import OpgeeException

_logger = getLogger(__name__)


class CrudeOilDewatering(Process):
    # For our initial, highly-simplified test case, we just shuttle the oil and water
    # to two output streams and force the temperature and pressure to what was in the
    # OPGEE v3 workbook for the default field.
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.temperature_heater_treater = self.attr("temperature_heater_treater")
        self.heat_loss = self.attr("heat_loss")
        self.prime_mover_type = self.attr("prime_mover_type")
        self.eta_gas = (self.attr("eta_gas")).to("frac")
        self.eta_electricity = (self.attr("eta_electricity")).to("frac")
        self.oil_path = field.attr("oil_processing_path")
        self.oil_path_dict = {"Stabilization": "oil for stabilization",
                              "Storage": "oil for storage",
                              "Upgrading": "oil for upgrader",
                              "Dilution": "oil for dilution"}

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        # mass rate
        input = self.find_input_stream("crude oil")

        if input.is_uninitialized():
            return

        pressure = input.pressure
        oil_rate = input.flow_rate("oil", PHASE_LIQUID)
        water_rate = input.flow_rate("H2O", PHASE_LIQUID)
        temp = self.temperature_heater_treater if field.heater_treater else input.temperature

        separator_final_SOR = field.get_process_data("separator_final_SOR")

        try:
            output = self.oil_path_dict[self.oil_path]
        except:
            raise OpgeeException(f"{self.name} oil path is not recognized:{self.oil_path}. "
                                 f"Must be one of {list(self.oil_path_dict.keys())}")
        output_oil = self.find_output_stream(output)
        output_oil.set_liquid_flow_rate("oil", oil_rate, temp, pressure)

        water_to_treatment = self.find_output_stream("water")
        water_to_treatment.set_liquid_flow_rate("H2O", water_rate, temp, pressure)

        average_oil_temp = ureg.Quantity((input.temperature.m+self.temperature_heater_treater.m)/2, "degF")
        oil_heat_capacity = self.field.oil.specific_heat(self.field.oil.API, average_oil_temp)
        water_heat_capacity = self.field.water.specific_heat(average_oil_temp)
        delta_temp = ureg.Quantity(self.temperature_heater_treater.m - input.temperature.m, "delta_degF")
        heat_duty = ureg.Quantity(0, "mmBtu/day")
        if field.heater_treater:
            eff = (1 + self.heat_loss.to("frac")).to("frac")
            heat_duty = ((oil_rate * oil_heat_capacity + water_rate * water_heat_capacity) *
                         delta_temp * eff).to("mmBtu/day")

        # energy_use
        energy_use = self.energy
        energy_carrier = EN_NATURAL_GAS if self.prime_mover_type == "NG_engine" else EN_ELECTRICITY
        energy_consumption =\
            heat_duty / self.eta_gas if self.prime_mover_type == "NG_engine" else heat_duty / self.eta_electricity
        energy_use.set_rate(energy_carrier, energy_consumption.to("mmBtu/day"))

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)
