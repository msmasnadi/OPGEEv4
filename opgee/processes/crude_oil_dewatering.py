from opgee import ureg
from ..emissions import EM_COMBUSTION
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY
from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID

_logger = getLogger(__name__)


class CrudeOilDewatering(Process):
    # For our initial, highly-simplified test case, we just shuttle the oil and water
    # to two output streams and force the temperature and pressure to what was in the
    # OPGEE v3 workbook for the default field.
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()

        # TODO: capture these in Field instance vars instead, once for all processes
        self.heater_treater = field.attr("heater_treater")
        self.stab_column = field.attr("stabilizer_column")
        self.upgrader_type = field.attr("upgrader_type")
        self.frac_diluent = field.attr("fraction_diluent")

        self.temperature_heater_treater = self.attr("temperature_heater_treater")
        self.heat_loss = self.attr("heat_loss")
        self.prime_mover_type = self.attr("prime_mover_type")
        self.eta_gas = (self.attr("eta_gas")).to("frac")
        self.eta_electricity = (self.attr("eta_electricity")).to("frac")

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        input = self.find_input_stream("crude oil")
        temperature = input.temperature
        pressure = input.pressure
        oil_rate = input.flow_rate("oil", PHASE_LIQUID)
        water_rate = input.flow_rate("H2O", PHASE_LIQUID)

        separator_final_SOR = self.field.get_process_data("separator_final_SOR")

        oil_to_stabilization = self.find_output_stream("oil for stabilization", raiseError=False)
        temp = self.temperature_heater_treater if self.heater_treater else temperature
        if oil_to_stabilization is not None:
            oil_to_stabilization.set_liquid_flow_rate("oil", oil_rate, temp, pressure)

        water_to_treatment = self.find_output_stream("water")
        water_to_treatment.set_liquid_flow_rate("H2O", water_rate, temp, pressure)

        oil_to_storage = self.find_output_stream("oil for storage", raiseError=False)
        if oil_to_storage is not None:
            oil_to_storage.set_liquid_flow_rate("oil", oil_rate, temp, pressure)
        else:
            oil_to_upgrader = self.find_output_stream("oil for upgrader", raiseError=False)
            if oil_to_upgrader is not None:
                oil_to_upgrader.set_liquid_flow_rate("oil", oil_rate, temp, pressure)
            else:
                oil_to_dilution = self.find_output_stream("oil for dilution", raiseError=False)
                if oil_to_dilution is not None:
                    oil_to_dilution.set_liquid_flow_rate("oil", oil_rate, temp, pressure)

        average_oil_temp = ureg.Quantity((temperature.m+self.temperature_heater_treater.m)/2, "degF")
        oil_heat_capacity = self.field.oil.specific_heat(self.field.oil.API, average_oil_temp)
        water_heat_capacity = self.field.water.specific_heat(average_oil_temp)
        delta_temp = ureg.Quantity(self.temperature_heater_treater.m - temperature.m, "delta_degF")
        heat_duty = ureg.Quantity(0, "mmBtu/day")
        if self.heater_treater:
            eff = (1 + self.heat_loss.to("frac")).to("frac")
            heat_duty = ((oil_rate * oil_heat_capacity + water_rate * water_heat_capacity) *
                         delta_temp * eff).to("mmBtu/day")

        # energy_use
        energy_use = self.energy
        energy_carrier = EN_NATURAL_GAS if self.prime_mover_type == "NG_engine" else EN_ELECTRICITY
        energy_consumption = heat_duty / self.eta_gas if self.prime_mover_type == "NG_engine" else heat_duty / self.eta_electricity
        energy_use.set_rate(energy_carrier, energy_consumption.to("mmBtu/day"))

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combusion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "CO2", combusion_emission)
