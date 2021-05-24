from ..log import getLogger
from ..process import Process
from ..thermodynamics import Hydrocarbon
from opgee import ureg

_logger = getLogger(__name__)

dict_chemical = Hydrocarbon.get_dict_chemical()


class Separation(Process):
    def run(self, analysis):
        self.print_running_msg()

    def impute(self):
        field = self.get_field()

        gas_after = self.get_gas_stream(field)

        oil_after = field.find_stream("oil after separator")
        water_after = field.find_stream("water after separator")
        gas_after = field.find_stream("gas after separator")
        gas_fugitives = field.find_stream("gas fugitives from separator")

        oil_before = field.find_stream("oil before separator")
        water_before = field.find_stream("water before separator")
        gas_before = field.find_stream("gas before separator")

        downhole_pump = field.find_process("DownholePump")
        wellhead_temp = downhole_pump.attr("wellhead_temperature")
        wellhead_press = downhole_pump.attr("wellhead_pressure")
        for stream in [oil_before, water_before, gas_before]:
            stream.set_temperature_and_pressure(wellhead_temp, wellhead_press)

        oil_before.copy_flow_rates_from(oil_after)
        water_before.copy_flow_rates_from(water_after)
        gas_before.copy_flow_rates_from(gas_after)
        gas_before.add_flow_rates_from(gas_fugitives)

    def get_gas_stream(self, field):
        """

        :return:
        """
        oil_volume_rate = field.attr("oil_prod")              # (float) bbl/day
        gas_oil_ratio = field.attr("GOR")                   # (float) scf/bbl
        gas_comp = field.attrs_with_prefix("gas_comp_")     # Pandas.Series (float) percent
        temperature = self.attr("temperature_outlet").to("kelvin").m
        pressure = self.attr("gas_pressure_after_boosting").to("Pa").m
        #TODO: delete this when the OPGEE updated the issue #376
        std_temp = field.model.const("std-temperature").to("kelvin").m
        std_press = field.model.const("std-pressure").to("Pa").m

        gas_after = field.find_stream("gas after separator")
        for component in gas_comp.keys():
            mol_frac = gas_comp[component]
            gas_volume_rate = oil_volume_rate * gas_oil_ratio * mol_frac.to("frac")
            # gas_density = ureg.Quantity(dict_chemical[component].rho("g", temperature, pressure), "kg/m**3")
            # TODO: delete this when the OPGEE updated the issue #376
            gas_density = ureg.Quantity(dict_chemical[component].rho("g", std_temp, std_press), "kg/m**3")
            gas_mass_rate = gas_volume_rate.to("m**3/day") * gas_density.to("tonne/m**3")
            gas_after.set_gas_flow_rate(component, gas_mass_rate.m)
        gas_after.set_temperature_and_pressure(temperature, pressure)
        return gas_after