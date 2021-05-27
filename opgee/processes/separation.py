from ..log import getLogger
from ..process import Process
from ..thermodynamics import Hydrocarbon
from opgee import ureg
from opgee.stream import Stream

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



        gas_before = field.find_stream("gas from downhole pump to separator")
        oil_before = field.find_stream("oil from downhole pump to separator")
        water_before = field.find_stream("water from downhole pump to separator")

        downhole_pump = field.find_process("DownholePump")
        wellhead_temp = downhole_pump.attr("wellhead_temperature")
        wellhead_press = downhole_pump.attr("wellhead_pressure")
        for stream in [oil_before, water_before, gas_before]:
            stream.set_temperature_and_pressure(wellhead_temp, wellhead_press)



        # oil_after = field.find_stream("oil after separator")
        # water_after = field.find_stream("water after separator")
        gas_after = self.get_gas_stream(field)
        oil_after = self.get_oil_stream(field, gas_after)
        gas_fugitives = field.find_stream("gas fugitives from separator")

        oil_before.copy_flow_rates_from(oil_after)
        water_before.copy_flow_rates_from(water_after)
        gas_before.copy_flow_rates_from(gas_after)
        gas_before.add_flow_rates_from(gas_fugitives)

    def get_gas_stream(self, field):
        """

        :param field:
        :return:
        """
        oil_volume_rate = field.attr("oil_prod")                                                                        # (float) bbl/day
        gas_oil_ratio = field.attr("GOR")                                                                               # (float) scf/bbl
        gas_comp = field.attrs_with_prefix("gas_comp_")                                                                 # Pandas.Series (float) percent
        temperature = self.attr("temperature_outlet").to("kelvin")
        pressure = self.attr("gas_pressure_after_boosting").to("Pa").m
        std_temp = field.model.const("std-temperature").to("kelvin").m
        std_press = field.model.const("std-pressure").to("Pa").m

        gas_after = field.find_stream("gas after separator")
        for component in gas_comp.keys():
            mol_frac = gas_comp[component]
            gas_volume_rate = oil_volume_rate * gas_oil_ratio * mol_frac.to("frac")
            gas_density = ureg.Quantity(dict_chemical[component].rho("g", std_temp, std_press), "kg/m**3")
            gas_mass_rate = gas_volume_rate.to("m**3/day") * gas_density.to("tonne/m**3")
            gas_after.set_gas_flow_rate(component, gas_mass_rate)
        gas_after.set_temperature_and_pressure(temperature, pressure)
        return gas_after

    def get_oil_stream(self, field, gas_after):
        """

        :param field:
        :param gas_after:
        :return:
        """
        num_of_stages = self.attr("number_stages")
        temperature_stage1 = field.find_process("DownholePump").attr("wellhead_temperature")
        temperature_stage2 = (temperature_stage1.to("kelvin") + self.attr("temperature_outlet").to("kelvin")) / 2
        temperature_stage3 = self.attr("temperature_outlet")
        temperature_of_stages = [temperature_stage1, temperature_stage2.to("degF"), temperature_stage3]
        pressure_stage1 = self.attr("pressure_first_stage")
        pressure_stage2 = self.attr("pressure_second_stage")
        pressure_stage3 = self.attr("pressure_third_stage")
        pressure_of_stages = [pressure_stage1, pressure_stage2, pressure_stage3]
        gas_oil_ratio = field.attr("GOR")
        std_temp = field.model.const("std-temperature").to("kelvin").m
        std_press = field.model.const("std-pressure").to("Pa").m
        water_density_STP = ureg.Quantity(dict_chemical["H2O"].rho("l", std_temp, std_press), "kg/m**3")

        gas_specific_gravity = field.gas.specific_gravity(gas_after)
        stream = Stream("stages_stream", temperature=temperature_of_stages[num_of_stages - 1], pressure=pressure_of_stages[num_of_stages - 1])
        solution_GOR = field.oil.solution_gas_oil_ratio(stream)
        density = field.oil.density(stream)
        specific_gravity = (density / water_density_STP.to("lb/ft**3")).to("frac")

    # def free_gas_not_in_solution_of_stages(self, temperature_of_stages, pressure_of_stages)




