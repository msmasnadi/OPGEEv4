from ..core import OpgeeObject
import numpy as np
from ..opgee_tools_wl.constant import moles_of_gas_per_SCF_STP
from thermosteam import Chemical, Mixture
from ..stream import PHASE_GAS, PHASE_SOLID, PHASE_LIQUID, Stream
from .. import ureg
from pandas import Series


class WetAir(OpgeeObject):
    def __init__(self):
        self.components = ["N2", "O2", "CO2", "H2O"]
        self.mol_fraction = [0.774396, 0.20531, 0.000294, 0.02]
        self.mixture = Mixture.from_chemicals(self.components)

    def mol_weight(self):
        return self.mixture.MW(self.mol_fraction)

class DryAir(OpgeeObject):
    def __init__(self):
        self.components = ["N2", "O2", "Ar", "CO2"]
        self.mol_fraction = [0.780799398, 0.209449109, 0.009339514, 0.000411979]
        self.mixture = Mixture.from_chemicals(self.components)

    def mol_weight(self):
        return self.mixture.MW(self.mol_fraction)

    def density(self):
        return self.mixture.get_property("rho","kg/m3", "g", mol_fraction, T = 298.15, P = 10100)

class Hydrocarbon(OpgeeObject):
    dict_chemical = None

    def __init__(self, res_temp, res_press):
        self.res_temp = res_temp
        self.res_press = res_press
        self.dict_chemical = self.get_dict_chemical()

    def get_dict_chemical(self):
        if self.dict_chemical:
            return self.dict_chemical

        carbon_number = [f'C{n + 1}' for n in range(Stream.max_carbon_number)]
        saturated_hydrocarbon = ["CH4"] + [f'C_{n + 1}H_{2 * n + 4}' for n in range(1, Stream.max_carbon_number)]
        carbon_number_to_molecule = {carbon_number[i]: saturated_hydrocarbon[i] for i in range(len(carbon_number))}
        dict_chemical = {name: Chemical(carbon_number_to_molecule[name]) for name in carbon_number}
        non_hydrocarbon_gases = ["N2", "O2", "CO2", "H2O", "CO2", "H2", "H2S", "SO2"]
        dict_non_hydrocarbon = {name: Chemical(name) for name in non_hydrocarbon_gases}
        dict_chemical.update(dict_non_hydrocarbon)
        Hydrocarbon.dict_chemical = dict_chemical
        return dict_chemical

class Oil(Hydrocarbon):
    # Bubblepoint pressure constants
    pbub_a1 = 5.527215
    pbub_a2 = 0.783716
    pbub_a3 = 1.841408

    # Isothermal compressibility constants
    iso_comp_a1 = -0.000013668
    iso_comp_a2 = -0.00000001925682
    iso_comp_a3 = 0.02408026
    iso_comp_a4 = -0.0000000926091

    # Oil FVF constants
    oil_FVF_bub_a1 = 1
    oil_FVF_bub_a2 = 5.253E-07
    oil_FVF_bub_a3 = 1.81E-04
    oil_FVF_bub_a4 = 4.49E-04
    oil_FVF_bub_a5 = 2.06E-04

    # Oil lower heating value correlation
    oil_LHV_a1 = 1.68E+04
    oil_LHV_a2 = 5.44E+01
    oil_LHV_a3 = 2.17E-01
    oil_LHV_a4 = 1.90E-03

    # TODO: field.model.const("std-temperature")
    def __init__(self, API, gas_comp, gas_oil_ratio, res_temp, res_press):

        """

        :param API: (float) API gravity
        :param gas_comp: (panda.Series, float) Produced gas composition; unit = fraction
        :param gas_oil_ratio: (float) The ratio of the volume of gas that comes out of solution to the volume of oil at standard conditions; unit = fraction
        :param reservoir_temperature: (float) average reservoir temperature; unit = F
        :param reservoir_pressure: (float) average reservoir pressure; unit = psia
        """
        super().__init__(res_temp, res_press)
        self.API = API
        self.oil_specific_gravity = 141.5 / (131.5 + API.m)
        self.gas_comp = gas_comp
        self.gas_oil_ratio = gas_oil_ratio
        self.wet_air_MW = WetAir().mol_weight()

    def gas_specific_gravity(self):
        """
        Gas specific gravity is defined as the ratio of the molecular weight (MW) of the gas
        to the MW of wet air

        :return: (float) gas specific gravity (unit = fraction)
        """
        gas_comp = self.gas_comp
        gas_SG = 0
        for component, mol_frac in gas_comp.items():
            molecular_weight = self.dict_chemical[component].MW
            gas_SG += molecular_weight * mol_frac
        return gas_SG / self.wet_air_MW

    # TODO: pint cannot handle this unit. Talk to Rich
    # @staticmethod
    # def specific_gravity(self):
    #     API = self.API
    #     return 141.5 / (131.5 + API.m)

    def bubble_point_solution_GOR(self):
        """
        R_sb = 1.1618 * R_sp
        R_Sb is GOR at bubblepoint, R_sp is GOR at separator
        Valco and McCain (2002) give a means to estimate the bubble point gas-oil ratio from the separator gas oil ratio.
        Since OPGEE takes separator gas oil ratio as an input, we use this

        :return:(float) GOR at bubblepoint (unit = fraction)
        """
        #TODO: ask Rich if the unit comment is needed
        gor = self.gas_oil_ratio
        return gor * 1.1618

    def reservoir_solution_GOR(self):
        """
        The solution gas oil ratio (GOR) at resevoir condition is
        the minimum of empirical correlation and bubblepoint GOR

        :return: (float) solution gas oil ratio at resevoir condition (unit = fraction)
        """
        oil_SG = self.oil_specific_gravity
        res_temperature = self.res_temp.to("rankine").m
        res_pressure = self.res_press.m
        gas_SG = self.gas_specific_gravity()
        gor_bubble = self.bubble_point_solution_GOR()

        result = np.min([
            res_pressure ** (1 / self.pbub_a2) *
            oil_SG ** (-self.pbub_a1 / self.pbub_a2) *
            np.exp(self.pbub_a3 / self.pbub_a2 * gas_SG * oil_SG) /
            (res_temperature * gas_SG) ,
            gor_bubble
        ])
        return result

    def bubble_point_pressure(self):
        """

        :return: (float) bubblepoint pressure (unit = psia)
        """
        API = self.API
        gas_comp = self.gas_comp
        GOR = self.gas_oil_ratio
        oil_SG = self.oil_specific_gravity
        res_temperature = self.res_temp.to("rankine").m

        gas_SG = self.gas_specific_gravity()
        gor_bubble = self.bubble_point_solution_GOR()

        result = (oil_SG ** self.pbub_a1 *
                  (gas_SG * gor_bubble * res_temperature) ** self.pbub_a2 *
                  np.exp(-self.pbub_a3 * gas_SG * oil_SG))
        return result

    def bubble_point_formation_volume_factor(self):
        """
        the formation volume factor is defined as the ratio of the volume of oil (plus the gas in solution)
        at the prevailing reservoir temperature and pressure to the volume of oil at standard conditions

        :return: (float) bubblepoint formation volume factor (unit = fraction)
        """
        oil_SG = self.oil_specific_gravity
        res_temperature = self.res_temp.m

        gas_SG = self.gas_specific_gravity()
        res_GOR = self.reservoir_solution_GOR()

        result = (self.oil_FVF_bub_a1 + self.oil_FVF_bub_a2 * res_GOR * (res_temperature - 60) +
                  self.oil_FVF_bub_a3 * res_GOR / oil_SG + self.oil_FVF_bub_a4 * (res_temperature - 60) /
                  oil_SG + self.oil_FVF_bub_a5 * res_GOR * gas_SG / oil_SG)
        return result

    def solution_gas_oil_ratio(self, stream):
        """
        The solution gas-oil ratio (GOR) is a general term for the amount of gas dissolved in the oil

        :return: (float) solution gas oil ratio (unit = fraction)
        """
        API = self.API
        gas_comp = self.gas_comp
        GOR = self.gas_oil_ratio
        oil_SG = self.oil_specific_gravity
        stream_temp = stream.temperature.to("rankine").m
        stream_press = stream.pressure.m

        gas_SG = self.gas_specific_gravity()
        gor_bubble = self.bubble_point_solution_GOR()

        result = np.min([np.power(stream_press, 1 / self.pbub_a2) *
                        np.power(oil_SG, -self.pbub_a1 / self.pbub_a2) *
                        np.exp(self.pbub_a3 / self.pbub_a2 * gas_SG * oil_SG) *
                        1 / (stream_temp * gas_SG),
                        gor_bubble])
        return result
        #TODO:
        # 3. ask Adam to get the formula reference
        # temp1 = np.power(stream.pressure, 1 / pbub_a2)
        # temp2 = np.power(oil_SG, -pbub_a1 / pbub_a2)
        # temp3 = np.exp(pbub_a3 / pbub_a2 * gas_SG * oil_SG)
        # TODO: unit coversion, ask Rich if this in the correct conversion
        # temp4 = 1 / (stream.temperature.to("rankine") * gas_SG)
        # return np.min([temp1 * temp2 * temp3 * temp4, gor_bubble])

    def saturated_formation_volume_factor(self, stream):
        """
        the formation volume factor is defined as the ratio of the volume of oil (plus the gas in solution)
        at the prevailing reservoir temperature and pressure to the volume of oil at standard conditions

        :return: (float) saturated formation volume factor (unit = fraction)
        """
        API = self.API
        gas_comp = self.gas_comp
        oil_SG = self.oil_specific_gravity
        stream_temp = stream.temperature.m

        gas_SG = self.gas_specific_gravity()
        solution_gor = self.solution_gas_oil_ratio(stream)

        result = (1 + 0.000000525 * solution_gor * (stream_temp - 60) +
                  0.000181 * solution_gor / oil_SG + 0.000449 * (stream_temp - 60) / oil_SG +
                  0.000206 * solution_gor * gas_SG / oil_SG)
        return result

    def unsat_formation_volume_factor(self, stream):
        """
        the formation volume factor is defined as the ratio of the volume of oil (plus the gas in solution)
        at the prevailing reservoir temperature and pressure to the volume of oil at standard conditions

        :return: (float) unsaturated formation volume factor (unit = fraction)
        """
        bubble_oil_FVF = self.bubble_point_formation_volume_factor()
        p_bubblepoint = self.bubble_point_pressure()
        stream_press = stream.pressure.m

        result = bubble_oil_FVF * np.exp(self.isothermal_compressibility() * (p_bubblepoint - stream_press))
        return result

    def isothermal_compressibility_X(self, stream):
        """
        Isothermal compressibility is the change in volume of a system as the pressure changes while temperature remains constant.

        :return:
        """
        solution_gor = self.solution_gas_oil_ratio(stream)
        gas_SG = self.gas_specific_gravity()
        stream_temp = stream.temperature.to("rankine").m

        result = (self.iso_comp_a1 * solution_gor + self.iso_comp_a2 * solution_gor ** 2 +
                  self.iso_comp_a3 * gas_SG + self.iso_comp_a4 * stream_temp ** 2)
        return max(result, 0)

    def isothermal_compressibility(self):
        """
        Regression from ...

        :return:
        """
        oil_SG = self.oil_specific_gravity
        result = (55.233 - 60.588 * oil_SG) / 1e6
        return result

    def formation_volume_factor(self, stream):
        """
        the formation volume factor is defined as the ratio of the volume of oil (plus the gas in solution)
        at the prevailing reservoir temperature and pressure to the volume of oil at standard conditions

        :return:(float) final formation volume factor (unit = fraction)
        """
        p_bubblepoint = self.bubble_point_pressure()

        if stream.pressure < p_bubblepoint:
            result = self.saturated_formation_volume_factor(stream)
        else:
            result = self.unsat_formation_volume_factor()
        return result

    def density(self):
        """
        crude oil density

        :return: (float) crude oil density (unit = lb/ft3)
        """
        oil_SG = self.oil_specific_gravity

        gas_SG = self.gas_specific_gravity()
        solution_gor = self.solution_gas_oil_ratio()
        volume_factor = self.volume_factor()

        result = (62.42796 * oil_SG + 0.0136 * gas_sg * solution_gor) / volume_factor
        return result

    def mass_energy_density(self):
        """

        :return:(float) mass energy density (unit = btu/lb)
        """
        API = self.API

        result = (oil_LHV_a1 + oil_LHV_a2 * API -
                  oil_LHV_a3 * API**2 - oil_LHV_a4 * F31**3)
        return result

    #TODO: cut this into the Hydrocarbon class
    def volume_energy_density(self):
        """

        :return:(float) volume energy density (unit = J/m3)
        """
        mass_energy_density = self.mass_energy_density()
        density = self.density()

        result = mass_energy_density * density * 1e+6
        return result

    def energy_flow_rate(self, stream):
        """

        :return:(float) energy flow rate (unit = btu/day)
        """
        mass_flow_rate = stream.hydrocarbon_rate(PHASE_LIQUID)
        mass_energy_density = self.mass_energy_density()

        result = mass_energy_density * mass_flow_rate.to("lb/day")
        return result


class Gas(Hydrocarbon):
    #TODO: ask Rich where to put the global constant
    ambient_temperature = ureg.Quantity(60, "degF")
    ambient_pressure = ureg.Quantity(14.676, "psi")

    def __init__(self, res_temp, res_press):
        super().__init__(res_temp, res_press)
        self.dry_air_MW = DryAir().mol_weight()

    def total_molar_flow_rate(self, stream):
        """

        :param stream:
        :return: (float) total molar flow rate (unit = mol/day)
        """
        mass_flow_rate = stream.total_gases_rates() #pandas.Series
        total_molar_flow_rate = 0
        for component, tonne_per_day in mass_flow_rate.items():
            # TODO: ask Rich if i need to create unit for all the non-unit variable
            molecular_weight = ureg.Quantity(self.dict_chemical[component].MW, "g/mol")
            total_molar_flow_rate += tonne_per_day.to("g/day") / molecular_weight

        return total_molar_flow_rate

    def component_molar_fraction(self, name, stream):
        """

        :param name: (str) component name
        :param stream:
        :return:
        """
        total_molar_flow_rate = self.total_molar_flow_rate(stream)
        mass_flow_rate = stream.gas_flow_rate(name)
        molar_flow_rate = mass_flow_rate.to("g/day") / self.dict_chemical[name].MW

        result = molar_flow_rate / total_molar_flow_rate
        return result

    def specific_gravity(self, stream):
        """

        :param stream:
        :return:
        """
        mass_flow_rate = stream.total_gases_rates() #pandas.Series
        specific_gravity = 0
        for component, tonne_per_day in mass_flow_rate.items():
            molecular_weight = self.dict_chemical[component].MW
            molar_fraction = self.component_molar_fraction(component, stream)
            specific_gravity += molar_fraction * molecular_weight

        return specific_gravity / self.wet_air_MW

    def ratio_of_specific_heat(self, stream):
        """

        :param stream:
        :return:
        """
        mass_flow_rate = stream.total_gases_rates()  # pandas.Series
        universal_gas_constants = 8.31446261815324   # J/mol/K
        ratio_of_specific_heat = 0
        for component, tonne_per_day in mass_flow_rate.items():
            molecular_weight = self.dict_chemical[component].MW
            gas_constant = universal_gas_constants / molecular_weight
            Cp = self.dict_chemical[component].cp(phase = 'g', T = 298.15)
            Cv = Cp + gas_constant
            ratio_of_specific_heat += Cp / Cv

        return ratio_of_specific_heat

    def uncorrelated_pseudocritical_temperature_and_pressure(self, stream):
        """

        :param stream:
        :return:(float) pandas.Series
        """
        mass_flow_rate = stream.total_gases_rates()  # pandas.Series
        temp1 = 0; temp2 = 0; temp3 = 0
        temperature = 0; presure = 0
        for component, tonne_per_day in mass_flow_rate.items():
            molar_fraction = self.component_molar_fraction(component, stream)
            critical_temperature = ureg.Quantity(dict_chemical[component].Tc, "kelvin").to("rankine")
            critical_pressure = ureg.Quantity(dict_chemical[component].Pc, "Pa").to("psi")
            temp1 += molar_fraction * critical_temperature.m / critical_pressure.m**0.5
            temp2 += molar_fraction * critical_temperature.m / critical_pressure.m
            temp3 += molar_fraction * (critical_temperature.m / critical_pressure.m)**0.5
        temp1 = temp1**2
        temp2 = 1/3 * temp2
        temp3 = 2/3 * temp3**2
        temperature = ureg.Quantity(temp1 / (temp2 + temp3), "rankine")
        pressure = ureg.Quantity(temp1 / (temp2 + temp3)**2, "psi")
        return Series(data = [temperature, pressure], index=["temperature", "pressure"])

    def correlated_pseudocritical_temperature(self, stream):
        """

        :param stream:
        :return:
        """
        uncorr_pseudocritical_temp = self.uncorrelated_pseudocritical_temperature_and_pressure(stream)["temperature"]
        molar_frac_O2 = self.component_molar_fraction("O2", stream)
        molar_frac_H2S = self.component_molar_fraction("H2S", stream)
        result = (uncorr_pseudocritical_temp -
                  120 * ((molar_frac_O2 + molar_frac_H2S) ** 0.9 - (molar_frac_O2 + molar_frac_H2S) ** 1.6) +
                  15 * (molar_frac_H2S ** 0.5 - molar_frac_H2S ** 4)
                  )
        return result

    def correlated_pseudocritical_pressure(self, stream):
        """

        :param stream:
        :return:
        """
        uncorr_pseudocritical_temp = self.uncorrelated_pseudocritical_temperature_and_pressure(stream)["temperature"]
        uncorr_pseudocritical_press = self.uncorrelated_pseudocritical_temperature_and_pressure(stream)["pressure"]
        corr_pseudocritical_temp = self.correlated_pseudocritical_temperature(stream)
        molar_frac_H2S = self.component_molar_fraction("H2S", stream)

        result = ((uncorr_pseudocritical_press * corr_pseudocritical_temp) /
                  (uncorr_pseudocritical_temp -
                   molar_frac_H2S * (1 - molar_frac_H2S) *
                   (uncorr_pseudocritical_temp - corr_pseudocritical_temp)))

        return result

    def reduced_temperature(self, stream):
        """

        :param stream:
        :return:
        """
        corr_pseudocritical_temp = self.correlated_pseudocritical_temperature(stream)
        result = stream.temperature.to("rankine") / corr_pseudocritical_temp

        return result

    def reduced_pressure(self, stream):
        """

        :param stream:
        :return:
        """
        corr_pseudocritical_press = self.correlated_pseudocritical_pressure(stream)
        result = stream.pressure / corr_pseudocritical_press

        return result

    def Z_factor(self, stream):
        """

        :param stream:
        :return:
        """
        reduced_temp = self.reduced_temperature(stream)
        reduced_press = self.reduced_pressure(stream)
        reduced_temp_dimensonless = reduced_temp.m
        reduced_press_dimensonless = reduced_press.m

        z_factor_A = 1.39 * (reduced_temp_dimensonless - 0.92) ** 0.5 - 0.36 * reduced_temp_dimensonless - 0.101
        z_factor_B = (reduced_press_dimensonless * (0.62 - 0.23 * reduced_temp_dimensonless) +
                      reduced_press_dimensonless ** 2 * (0.066 / (reduced_temp_dimensonless - 0.86) - 0.037) +
                      0.32 * reduced_temp_dimensonless ** 6 / (10 ** (9 * reduced_temp_dimensonless - 9)))
        z_factor_C = 0.132 - 0.32 * np.log10(reduced_temp_dimensonless)
        z_factor_D = 10 ** (0.3106 - 0.49 * reduced_temp_dimensonless + 0.1824 * reduced_temp_dimensonless ** 2)
        z_factor = (z_factor_A + (1 - z_factor_A) * np.exp(-1 * z_factor_B) + z_factor_C * p_r ** z_factor_D)

        return np.max([z_factor, 0.05])

    def volume_factor(self, stream):
        """

        :param stream:
        :return:
        """
        z_factor = self.Z_factor(stream)
        temp = stream.temperature.to("rankine")
        amb_temp = ambient.to("rankine")

        result = ambient_pressure.m * z_factor * temp.m / (stream.pressure.m * amb_temp.m)

        return result

    def density(self, stream):
        """

        :param stream:
        :return:
        """
        volume_factor = self.volume_factor(stream)
        specific_gravity = self.specific_gravity(stream)

        return


        #TODO: ask Rich, what is the best way to direct convert tonne/day to lb/day
        result = mass_energy_density * mass_flow_rate.to("lb/day")
        return result
