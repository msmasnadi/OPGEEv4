import numpy as np
from ..error import OpgeeException
from ..process import Process
from ..log import getLogger
from opgee import ureg
from opgee.stream import Stream, PHASE_GAS, PHASE_LIQUID, PHASE_SOLID

_logger = getLogger(__name__)


class DownholePump(Process):
    def run(self, analysis):
        self.print_running_msg()

        field = self.get_field()
        gas_oil_ratio = field.attr("GOR")
        res_temp = field.attr("res_temp")
        wellhead_press = field.attr("wellhead_pressure")
        wellhead_temp = field.attr("wellhead_temperature")
        oil_volume_rate = field.attr("oil_prod")
        eta_pump_well = self.attr("eta_pump_well")
        prod_tubing_diam = field.attr("well_diam")
        prod_tubing_radius = prod_tubing_diam / 2
        depth = field.attr("depth")
        friction_factor = self.attr("friction_factor")
        num_prod_wells = field.attr("num_prod_wells")
        prod_tubing_xsection_area = np.pi * prod_tubing_radius ** 2
        prod_tubing_volume = (prod_tubing_xsection_area * depth).to("ft**3")
        # gravitational_constant = field.model.const("gravitational-constant")
        gravitational_acceleration = field.model.const("gravitational-acceleration")

        # mass rate
        input = self.find_input_stream("crude oil")
        lift_gas = self.find_input_stream('lifting gas')
        input.add_flow_rates_from(lift_gas)

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)

        output = self.find_output_stream("crude oil")
        output.copy_flow_rates_from(input)
        output.subtract_gas_rates_from(gas_fugitives)
        output.set_temperature_and_pressure(wellhead_temp, wellhead_press)

        # energy use
        oil = field.oil
        water = field.water
        gas = field.gas
        solution_gas_oil_ratio_input = oil.solution_gas_oil_ratio(input,
                                                                  oil.oil_specific_gravity,
                                                                  oil.gas_specific_gravity,
                                                                  oil.gas_oil_ratio)
        solution_gas_oil_ratio_output = oil.solution_gas_oil_ratio(output,
                                                                   oil.oil_specific_gravity,
                                                                   oil.gas_specific_gravity,
                                                                   oil.gas_oil_ratio)
        oil_density_input = oil.density(input,
                                        oil.oil_specific_gravity,
                                        oil.gas_specific_gravity,
                                        oil.gas_oil_ratio)
        oil_density_output = oil.density(output,
                                         oil.oil_specific_gravity,
                                         oil.gas_specific_gravity,
                                         oil.gas_oil_ratio)
        volume_oil_lifted_input = oil.volume_flow_rate(input,
                                                       oil.oil_specific_gravity,
                                                       oil.gas_specific_gravity,
                                                       oil.gas_oil_ratio)
        volume_oil_lifted_output = oil.volume_flow_rate(output,
                                                        oil.oil_specific_gravity,
                                                        oil.gas_specific_gravity,
                                                        oil.gas_oil_ratio)

        # free_gas = gas_oil_ratio - solution_gas_oil_ratio_input

        # properties of crude oil (all at average conditions along wellbore, in production tubing)
        average_SOR = (solution_gas_oil_ratio_input + solution_gas_oil_ratio_output) / 2
        average_oil_density = (oil_density_input + oil_density_output) / 2
        average_volume_oil_lifted = (volume_oil_lifted_input + volume_oil_lifted_output).to("ft**3/day") / 2

        # properties of water (all at average conditions along wellbore, in production tubing)
        water_density = water.density()
        volume_water_lifted = (water.volume_flow_rate(output)).to("ft**3/day")

        # properties of free gas (all at average conditions along wellbore, in production tubing)
        free_gas = solution_gas_oil_ratio_input - average_SOR
        wellbore_average_press = (wellhead_press + input.pressure) / 2
        wellbore_average_temp = ureg.Quantity((wellhead_temp.m + res_temp.m) / 2, "degF")
        stream = Stream("average", temperature=wellbore_average_temp, pressure=wellbore_average_press)
        stream.copy_flow_rates_from(input)
        gas_FVF = gas.volume_factor(stream)
        gas_density = gas.density(stream)
        volume_free_gas = free_gas * gas_FVF
        volume_free_gas_lifted = (volume_free_gas * oil_volume_rate).to("ft**3/day")

        total_volume_fluid_lifted = (average_volume_oil_lifted +
                                     volume_water_lifted +
                                     volume_free_gas_lifted).to("ft**3/day")
        fluid_velocity = (total_volume_fluid_lifted / (prod_tubing_xsection_area * num_prod_wells)).to("ft/sec")

        total_mass_fluid_lifted = (average_oil_density * average_volume_oil_lifted +
                                   water_density * volume_water_lifted +
                                   gas_density * volume_free_gas_lifted).to("lb/day")
        fluid_lifted_density = (total_mass_fluid_lifted / total_volume_fluid_lifted).to("lb/ft**3")

        # downhole pump
        pressure_drop_elev = (fluid_lifted_density * gravitational_acceleration * depth).to("psi")
        pressure_drop_fric = (friction_factor * depth * fluid_velocity ** 2 /
                              (2 * prod_tubing_diam * gravitational_acceleration)).to("ft")







    def impute(self):
        output = self.find_output_stream("crude oil")

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives = self.set_gas_fugitives(output, 1 / (1 - loss_rate))

        input = self.find_input_stream("crude oil")
        input.add_flow_rates_from(output)
        input.add_flow_rates_from(gas_fugitives)
