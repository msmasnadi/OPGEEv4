import numpy as np
from ..energy import Energy, EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
from ..process import Process
from ..log import getLogger
from opgee import ureg
from opgee.stream import Stream
from ..stream import Stream, PHASE_GAS, PHASE_LIQUID, PHASE_SOLID
from ..emissions import Emissions, EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES

_logger = getLogger(__name__)


class DownholePump(Process):
    def run(self, analysis):
        self.print_running_msg()

        field = self.get_field()
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
        gravitational_acceleration = field.model.const("gravitational-acceleration")
        prime_mover_type = self.attr("prime_mover_type")

        # mass rate
        input = self.find_input_stream("crude oil")
        lift_gas = self.find_input_stream('lifting gas')
        input.add_flow_rates_from(lift_gas)

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)

        output = self.find_output_stream("crude oil")
        # Check
        self.set_iteration_value(output.total_flow_rate())
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

        # properties of crude oil (all at average conditions along wellbore, in production tubing)
        average_SOR = (solution_gas_oil_ratio_input + solution_gas_oil_ratio_output) / 2
        average_oil_density = (oil_density_input + oil_density_output) / 2
        average_volume_oil_lifted = (volume_oil_lifted_input + volume_oil_lifted_output).to("ft**3/day") / 2

        # properties of water (all at average conditions along wellbore, in production tubing)
        water_density = water.density()
        volume_water_lifted = water.volume_flow_rate(output)

        # properties of free gas (all at average conditions along wellbore, in production tubing)
        free_gas = solution_gas_oil_ratio_input - average_SOR
        wellbore_average_press = (wellhead_press + input.pressure) / 2
        wellbore_average_temp = ureg.Quantity((wellhead_temp.m + res_temp.m) / 2, "degF")
        stream = Stream("average", temperature=wellbore_average_temp, pressure=wellbore_average_press)
        stream.copy_flow_rates_from(input)
        gas_FVF = gas.volume_factor(stream)
        gas_density = gas.density(stream)
        volume_free_gas = free_gas * gas_FVF
        volume_free_gas_lifted = (volume_free_gas * oil_volume_rate)

        total_volume_fluid_lifted = (average_volume_oil_lifted +
                                     volume_water_lifted +
                                     volume_free_gas_lifted)
        fluid_velocity = (total_volume_fluid_lifted / (prod_tubing_xsection_area * num_prod_wells))

        total_mass_fluid_lifted = (average_oil_density * average_volume_oil_lifted +
                                   water_density * volume_water_lifted +
                                   gas_density * volume_free_gas_lifted)
        fluid_lifted_density = (total_mass_fluid_lifted / total_volume_fluid_lifted)

        # downhole pump
        pressure_drop_elev = fluid_lifted_density * gravitational_acceleration * depth
        pressure_drop_fric = (fluid_lifted_density * friction_factor * depth * fluid_velocity ** 2 /
                              (2 * prod_tubing_diam))
        pressure_drop_total = pressure_drop_fric + pressure_drop_elev
        pressure_for_lifting = max(0, wellhead_press + pressure_drop_total - input.pressure)
        liquid_flow_rate_per_well = (average_volume_oil_lifted + volume_water_lifted) / num_prod_wells
        brake_horse_power = 1.05 * (liquid_flow_rate_per_well * pressure_for_lifting) / eta_pump_well
        energy_consumption_of_stages = self.get_energy_consumption_stages(prime_mover_type, [brake_horse_power])
        energy_consumption_sum = sum(energy_consumption_of_stages) * num_prod_wells

        energy_use = self.energy
        if prime_mover_type == "NG_engine" or "NG_turbine":
            energy_carrier = EN_NATURAL_GAS
        elif prime_mover_type == "Electric_motor":
            energy_carrier = EN_ELECTRICITY
        else:
            energy_carrier = EN_DIESEL
        energy_use.set_rate(energy_carrier, energy_consumption_sum)

        # emission
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        process_EF = self.get_process_EF() # pandas Series
        combusion_emission = (energy_for_combustion * process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "GHG", combusion_emission)

        emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)


    def impute(self):
        output = self.find_output_stream("crude oil")

        loss_rate = self.venting_fugitive_rate()
        loss_rate = (1 / (1 - loss_rate)).to("frac")
        gas_fugitives = self.set_gas_fugitives(output, loss_rate)

        input = self.find_input_stream("crude oil")
        input.add_flow_rates_from(output)
        input.add_flow_rates_from(gas_fugitives)
