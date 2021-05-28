from ..log import getLogger
from ..process import Process
from ..thermodynamics import Hydrocarbon
from opgee import ureg
from opgee.stream import Stream, PHASE_GAS, PHASE_LIQUID, PHASE_SOLID

_logger = getLogger(__name__)

dict_chemical = Hydrocarbon.get_dict_chemical()


class Separation(Process):
    def run(self, analysis):
        self.print_running_msg()
        # TODO: check if gas lifting, CO2 flooding are needed
        lift_gas = self.find_input_streams('lifting gas', raiseError=False)
        flood_CO2 = self.find_input_streams('flooding CO2', raiseError=False)

    def impute(self):
        field = self.get_field()

        wellhead_temp = field.attr("wellhead_temperature")
        wellhead_press = field.attr("wellhead_pressure")

        gas_after, oil_after, water_after = self.get_output_streams(field)
        gas_fugitives = field.find_stream("gas fugitives from separator")
        # gas_fugitives = self.venting_fugitive_rate()

        output = Stream.combine([oil_after, gas_after, water_after], temperature=wellhead_temp, pressure=wellhead_press)
        output.add_flow_rates_from(gas_fugitives)

        input = self.find_input_streams("crude oil")
        input.set_temperature_and_pressure(wellhead_temp, wellhead_press)
        input.add_flow_rates_from(output)


    def get_output_streams(self, field):

        oil_volume_rate = field.attr("oil_prod")                        # (float) bbl/day

        gas_oil_ratio = field.attr("GOR")                               # (float) scf/bbl
        gas_comp = field.attrs_with_prefix("gas_comp_")                 # Pandas.Series (float) percent

        water_oil_ratio = field.attr("WOR")

        num_of_stages = self.attr("number_stages")

        std_temp = field.model.const("std-temperature")
        temperature_outlet = self.attr("temperature_outlet")
        temperature_stage1 = field.attr("wellhead_temperature")
        temperature_stage2 = (temperature_stage1.to("kelvin") + temperature_outlet.to("kelvin")) / 2
        temperature_of_stages = [temperature_stage1, temperature_stage2.to("degF"), temperature_outlet]

        std_press = field.model.const("std-pressure")
        pressure_after_boosting = self.attr("gas_pressure_after_boosting")
        pressure_stage1 = self.attr("pressure_first_stage")
        pressure_stage2 = self.attr("pressure_second_stage")
        pressure_stage3 = self.attr("pressure_third_stage")
        pressure_outlet = self.attr("pressure_outlet")
        pressure_of_stages = [pressure_stage1, pressure_stage2, pressure_stage3]

        oil = field.oil

        gas_after = field.find_stream("gas after separator")
        stream = Stream("stages_stream",
                        temperature=temperature_of_stages[num_of_stages - 1],
                        pressure=pressure_of_stages[num_of_stages - 1])
        density = oil.density(stream,  # lb/ft3
                              oil.oil_specific_gravity,
                              oil.gas_specific_gravity,
                              oil.gas_oil_ratio,
                              oil.res_temp)

        for component, mol_frac in gas_comp.items():
            gas_volume_rate = oil_volume_rate * gas_oil_ratio * mol_frac.to("frac")
            gas_density = field.oil.rho(component, std_temp, std_press, PHASE_GAS)
            gas_mass_rate = (gas_volume_rate * gas_density).to("tonne/day")
            gas_after.set_gas_flow_rate(component, gas_mass_rate)
        gas_after.set_temperature_and_pressure(temperature_outlet, pressure_after_boosting)

        oil_after = field.find_stream("oil after separator")
        oil_mass_rate = (oil_volume_rate * density).to("tonne/day")
        water_in_oil_mass_rate = (oil_mass_rate * self.attr("water_content_oil_emulsion")).to("tonne/day")
        oil_after.set_liquid_flow_rate("oil", oil_mass_rate)
        oil_after.set_liquid_flow_rate("H2O", water_in_oil_mass_rate)
        oil_after.set_temperature_and_pressure(temperature_outlet, pressure_outlet)

        water_density_STP = field.oil.rho("H2O", std_temp, std_press, PHASE_LIQUID)
        water_mass_rate = (oil_volume_rate * water_oil_ratio * water_density_STP.to("tonne/barrel_water") -
                           water_in_oil_mass_rate)
        water_after = field.find_stream("water after separator")
        water_after.set_liquid_flow_rate("H2O", water_mass_rate)
        water_after.set_temperature_and_pressure(temperature_outlet, pressure_outlet)
        return gas_after, oil_after, water_after