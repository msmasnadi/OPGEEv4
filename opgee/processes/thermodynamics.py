from ..core import OpgeeObject
import numpy as np
from thermosteam import Chemical, Mixture
from ..stream import PHASE_GAS, PHASE_SOLID, PHASE_LIQUID, Stream
from .. import ureg
from pandas import Series

class Air(OpgeeObject):
    """

    """
    def __init__(self, field):
        """

        :param field:
        """
        self.wet_air_composition = [("N2", 0.774396),
                                    ("O2", 0.20531),
                                    ("CO2", 0.000294),
                                    ("H2O", 0.02)]

        # self.dry_air_composition = [("N2", 0.780799398),
        #                             ("O2", 0.209449109),
        #                             ("Ar", 0.000294),
        #                             ("H2O", 0.02)]
        #
        self.dry_air_composition = [("N2", 0.79),
                                    ("O2", 0.21)]

        self.field = field

class WetAir(Air):
    """

    """
    def __init__(self, field):
        """

        :param field:
        """
        super().__init__(field)
        self.components = [name for name, fraction in self.wet_air_composition]
        self.mol_fraction = [fraction for name, fraction in self.wet_air_composition]
        self.mixture = Mixture.from_chemicals(self.components)

    def mol_weight(self):
        mol_weight = self.mixture.MW(self.mol_fraction)
        return ureg.Quantity(mol_weight, "g/mol")


class DryAir(Air):
    """

    """
    def __init__(self, field):
        """

        :param field:
        """
        super().__init__(field)
        self.components = [name for name, fraction in self.dry_air_composition]
        self.mol_fraction = [fraction for name, fraction in self.dry_air_composition]
        self.mixture = Mixture.from_chemicals(self.components)

    def mol_weight(self):
        """

        :return:
        """
        mol_weight = self.mixture.MW(self.mol_fraction)
        return ureg.Quantity(mol_weight, "g/mol")

    def density(self):
        """

        :return: (float) dry air density (unit = kg/m3)
        """
        std_temp = self.field.model.const("std-temperature").to("kelvin")
        std_press = self.field.model.const("std-pressure").to("Pa")
        rho = self.mixture.rho("g", self.mol_fraction, std_temp.m, std_press.m)
        return rho


class Hydrocarbon(OpgeeObject):
    """

    """
    dict_chemical = None

    def __init__(self, field):
        """

        :param field:
        """
        self.res_temp = field.attr("res_temp")
        self.res_press = field.attr("res_press")
        self.dict_chemical = self.get_dict_chemical()

    def get_dict_chemical(self):
        """

        :return:
        """
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
    """

    """
    # Bubblepoint pressure constants
    pbub_a1 = 5.527215
    pbub_a2 = 0.783716
    pbub_a3 = 1.841408

    def __init__(self, field):

        """

        :param API: (float) API gravity
        :param gas_comp: (panda.Series, float) Produced gas composition; unit = fraction
        :param gas_oil_ratio: (float) The ratio of the volume of gas that comes out of solution to the volume of oil at standard conditions; unit = fraction
        :param reservoir_temperature: (float) average reservoir temperature; unit = F
        :param reservoir_pressure: (float) average reservoir pressure; unit = psia
        """
        super().__init__(field)
        self.API = API = field.attr("API")
        self.oil_specific_gravity = 141.5 / (131.5 + API.m)
        self.gas_comp = field.attrs_with_prefix('gas_comp_')
        self.gas_oil_ratio = field.attr('GOR')
        self.wet_air_MW = WetAir(field).mol_weight()

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
            gas_SG += molecular_weight * mol_frac.m / 100
        return gas_SG / self.wet_air_MW

    def bubble_point_solution_GOR(self):
        """
        R_sb = 1.1618 * R_sp
        R_Sb is GOR at bubblepoint, R_sp is GOR at separator
        Valco and McCain (2002) give a means to estimate the bubble point gas-oil ratio from the separator gas oil ratio.
        Since OPGEE takes separator gas oil ratio as an input, we use this

        :return:(float) GOR at bubblepoint (unit = fraction)
        """
        gor = self.gas_oil_ratio
        result = gor * 1.1618
        return result.m

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
        GOR = self.gas_oil_ratio
        oil_SG = self.oil_specific_gravity
        res_temperature = self.res_temp.to("rankine").m

        gas_SG = self.gas_specific_gravity()
        gor_bubble = self.bubble_point_solution_GOR()

        result = (oil_SG ** self.pbub_a1 *
                  (gas_SG * gor_bubble * res_temperature) ** self.pbub_a2 *
                  np.exp(-self.pbub_a3 * gas_SG * oil_SG))
        return ureg.Quantity(result, "psi")

    def bubble_point_formation_volume_factor(self):
        """
        the formation volume factor is defined as the ratio of the volume of oil (plus the gas in solution)
        at the prevailing reservoir temperature and pressure to the volume of oil at standard conditions

        :return: (float) bubblepoint formation volume factor (unit = fraction)
        """
        # Oil FVF constants
        oil_FVF_bub_a1 = 1
        oil_FVF_bub_a2 = 5.253E-07
        oil_FVF_bub_a3 = 1.81E-04
        oil_FVF_bub_a4 = 4.49E-04
        oil_FVF_bub_a5 = 2.06E-04

        oil_SG = self.oil_specific_gravity
        res_temperature = self.res_temp.m

        gas_SG = self.gas_specific_gravity()
        res_GOR = self.reservoir_solution_GOR()

        result = (oil_FVF_bub_a1 + oil_FVF_bub_a2 * res_GOR * (res_temperature - 60) +
                  oil_FVF_bub_a3 * res_GOR / oil_SG + oil_FVF_bub_a4 * (res_temperature - 60) /
                  oil_SG + self.oil_FVF_bub_a5 * res_GOR * gas_SG / oil_SG)
        return result

    def solution_gas_oil_ratio(self, stream):
        """
        The solution gas-oil ratio (GOR) is a general term for the amount of gas dissolved in the oil

        :return: (float) solution gas oil ratio (unit = fraction)
        """
        API = self.API
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

    def saturated_formation_volume_factor(self, stream):
        """
        the formation volume factor is defined as the ratio of the volume of oil (plus the gas in solution)
        at the prevailing reservoir temperature and pressure to the volume of oil at standard conditions

        :return: (float) saturated formation volume factor (unit = fraction)
        """
        API = self.API
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
        p_bubblepoint = self.bubble_point_pressure().m
        stream_press = stream.pressure.m

        result = bubble_oil_FVF * np.exp(self.isothermal_compressibility() * (p_bubblepoint - stream_press))
        return result

    def isothermal_compressibility_X(self, stream):
        """
        Isothermal compressibility is the change in volume of a system as the pressure changes while temperature remains constant.

        :return:
        """
        # Isothermal compressibility constants
        iso_comp_a1 = -0.000013668
        iso_comp_a2 = -0.00000001925682
        iso_comp_a3 = 0.02408026
        iso_comp_a4 = -0.0000000926091

        solution_gor = self.solution_gas_oil_ratio(stream)
        gas_SG = self.gas_specific_gravity()
        stream_temp = stream.temperature.to("rankine").m

        result = (iso_comp_a1 * solution_gor + iso_comp_a2 * solution_gor ** 2 +
                  iso_comp_a3 * gas_SG + iso_comp_a4 * stream_temp ** 2)
        return max(result, 0.0)

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

    def density(self, stream):
        """
        crude oil density

        :return: (float) crude oil density (unit = lb/ft3)
        """
        oil_SG = self.oil_specific_gravity

        gas_SG = self.gas_specific_gravity()
        solution_gor = self.solution_gas_oil_ratio(stream)
        volume_factor = self.formation_volume_factor(stream)

        result = (62.42796 * oil_SG + 0.0136 * gas_SG * solution_gor) / volume_factor
        return ureg.Quantity(result, "lb/ft^3")

    def mass_energy_density(self):
        """

        :return:(float) mass energy density (unit = btu/lb)
        """
        # Oil lower heating value correlation
        oil_LHV_a1 = 16796
        oil_LHV_a2 = 54.4
        oil_LHV_a3 = 0.217
        oil_LHV_a4 = 0.0019

        API = self.API.m

        result = (oil_LHV_a1 + oil_LHV_a2 * API - oil_LHV_a3 * API**2 - oil_LHV_a4 * API**3)
        return ureg.Quantity(result, "british_thermal_unit/lb")

    def volume_energy_density(self, stream):
        """

        :return:(float) volume energy density (unit = mmBtu/bbl)
        """
        mass_energy_density = self.mass_energy_density()
        density = self.density(stream).to("lb/bbl_oil")

        result = mass_energy_density * density
        return result.to("mmBtu/bbl_oil")

    def energy_flow_rate(self, stream):
        """

        :return:(float) energy flow rate (unit = mmBtu/day)
        """
        mass_flow_rate = stream.hydrocarbon_rate(PHASE_LIQUID)
        #TODO: delete this line once the pint pandas works
        mass_flow_rate = ureg.Quantity(mass_flow_rate, "tonne/day")
        mass_flow_rate = mass_flow_rate.to("lb/day")
        mass_energy_density = self.mass_energy_density()

        result = mass_energy_density * mass_flow_rate
        return result.to("mmbtu/day")


class Gas(Hydrocarbon):
    """

    """
    def __init__(self, field):
        """

        :param field:
        """
        super().__init__(field)
        self.wet_air_MW = WetAir(field).mol_weight()
        self.dry_air = DryAir(field)
        self.field = field

    def total_molar_flow_rate(self, stream):
        """

        :param stream:
        :return: (float) total molar flow rate (unit = mol/day)
        """
        mass_flow_rate = stream.total_gases_rates() #pandas.Series
        total_molar_flow_rate = 0
        for component, tonne_per_day in mass_flow_rate.items():
            molecular_weight = ureg.Quantity(self.dict_chemical[component].MW, "g/mol")
            #TODO: delete this line once the pint pandas works
            tonne_per_day = ureg.Quantity(tonne_per_day, "tonne/day")
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
        #TODO: delete this line once the pint pandas works
        mass_flow_rate = ureg.Quantity(mass_flow_rate, "tonne/day")
        molecular_weight = ureg.Quantity(self.dict_chemical[name].MW, "g/mol")
        molar_flow_rate = mass_flow_rate.to("g/day") / molecular_weight

        result = molar_flow_rate / total_molar_flow_rate
        assert str(result.units) == "dimensionless"
        return result.m

    def specific_gravity(self, stream):
        """

        :param stream:
        :return:
        """
        mass_flow_rate = stream.total_gases_rates() #pandas.Series
        specific_gravity = 0
        for component, tonne_per_day in mass_flow_rate.items():
            molecular_weight = ureg.Quantity(self.dict_chemical[component].MW, "g/mol")
            molar_fraction = self.component_molar_fraction(component, stream)
            specific_gravity += molar_fraction * molecular_weight

        specific_gravity = specific_gravity / self.wet_air_MW

        assert str(specific_gravity.units) == "dimensionless"

        return specific_gravity.m

    def ratio_of_specific_heat(self, stream):
        """

        :param stream:
        :return:
        """
        mass_flow_rate = stream.total_gases_rates()  # pandas.Series
        universal_gas_constants = 8.31446261815324   # J/mol/K
        specific_heat_press = 0; specific_heat_volm = 0
        ratio_of_specific_heat = 0
        for component, tonne_per_day in mass_flow_rate.items():
            molecular_weight = self.dict_chemical[component].MW
            # TODO: delete this line once the pint pandas works
            tonne_per_day = ureg.Quantity(tonne_per_day, "tonne/day")
            kg_per_day = tonne_per_day.to("kg/day").m
            gas_constant = universal_gas_constants / molecular_weight
            Cp = self.dict_chemical[component].Cp(phase = 'g', T = 298.15)
            Cv = Cp - gas_constant
            specific_heat_press += kg_per_day * Cp
            specific_heat_volm += kg_per_day * Cv

        ratio_of_specific_heat = specific_heat_press / specific_heat_volm
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
            if tonne_per_day == 0:
                continue
            molar_fraction = self.component_molar_fraction(component, stream)
            critical_temperature = ureg.Quantity(self.dict_chemical[component].Tc, "kelvin").to("rankine")
            critical_pressure = ureg.Quantity(self.dict_chemical[component].Pc, "Pa").to("psi")
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
        uncorr_pseudocritical_temp = self.uncorrelated_pseudocritical_temperature_and_pressure(stream)["temperature"].m
        molar_frac_O2 = self.component_molar_fraction("O2", stream)
        molar_frac_H2S = self.component_molar_fraction("H2S", stream)
        result = (uncorr_pseudocritical_temp -
                  120 * ((molar_frac_O2 + molar_frac_H2S) ** 0.9 - (molar_frac_O2 + molar_frac_H2S) ** 1.6) +
                  15 * (molar_frac_H2S ** 0.5 - molar_frac_H2S ** 4)
                  )
        return ureg.Quantity(result, "rankine")

    def correlated_pseudocritical_pressure(self, stream):
        """

        :param stream:
        :return:
        """
        uncorr_pseudocritical_temp = self.uncorrelated_pseudocritical_temperature_and_pressure(stream)["temperature"].m
        uncorr_pseudocritical_press = self.uncorrelated_pseudocritical_temperature_and_pressure(stream)["pressure"].m
        corr_pseudocritical_temp = self.correlated_pseudocritical_temperature(stream).m
        molar_frac_H2S = self.component_molar_fraction("H2S", stream)

        result = ((uncorr_pseudocritical_press * corr_pseudocritical_temp) /
                  (uncorr_pseudocritical_temp -
                   molar_frac_H2S * (1 - molar_frac_H2S) *
                   (uncorr_pseudocritical_temp - corr_pseudocritical_temp)))

        return ureg.Quantity(result, "psi")

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
        z_factor = (z_factor_A + (1 - z_factor_A) * np.exp(-1 * z_factor_B)
                    + z_factor_C * reduced_press_dimensonless ** z_factor_D)

        return np.max([z_factor, 0.05])

    def volume_factor(self, stream):
        """

        :param stream:
        :return:
        """
        z_factor = self.Z_factor(stream)
        temp = stream.temperature.to("rankine")
        amb_temp = self.field.model.const("std-temperature").to("rankine").m
        amb_press = self.field.model.const("std-pressure").m

        result = amb_press * z_factor * temp.m / (stream.pressure.m * amb_temp)
        #TODO: assert dimensionless
        return result

    def density(self, stream):
        """

        :param stream:
        :return: (float) gas density (unit = tonne/day)
        """
        volume_factor = self.volume_factor(stream)
        specific_gravity = self.specific_gravity(stream)
        air_density_stp = ureg.Quantity(self.dry_air.density(), "kg/m**3")

        return air_density_stp.to("tonne/m**3") * specific_gravity / volume_factor

    def molar_weight(self, stream):
        """

        :param stream:
        :return:
        """
        mass_flow_rate = stream.total_gases_rates()  # pandas.Series
        molar_weight = ureg.Quantity(0, "g/mol")
        for component, tonne_per_day in mass_flow_rate.items():
            molecular_weight = ureg.Quantity(self.dict_chemical[component].MW, "g/mol")
            molar_fraction = self.component_molar_fraction(component, stream)
            molar_weight += molar_fraction * molecular_weight

        return molar_weight

    def volume_flow_rate(self, stream):
        """

        :param stream:
        :return:
        """
        #TODO: change this if pint pandas works
        total_mass_rate = ureg.Quantity(stream.total_gas_rate(), "tonne/day")
        density = self.density(stream)

        volume_flow_rate = total_mass_rate / density
        return volume_flow_rate

    def mass_energy_density(self, stream):
        """

        :param stream:
        :return: (float) gas mass energy density (unit = MJ/kg)
        """
        mass_flow_rate = stream.total_gases_rates()  # pandas.Series
        # TODO: change this if pint pandas works
        total_mass_rate = ureg.Quantity(stream.total_gas_rate(), "tonne/day")
        mass_energy_density = ureg.Quantity(0, "MJ/kg")
        for component, tonne_per_day in mass_flow_rate.items():
            if tonne_per_day == 0:
                continue
            LHV = self.dict_chemical[component].LHV
            if LHV < 0:
                LHV = -LHV
            LHV = ureg.Quantity(LHV, "joule/mol")
            LHV = LHV.to("MJ/mol")
            molecular_weight = ureg.Quantity(self.dict_chemical[component].MW, "g/mol")
            # TODO: delete this line once the pint pandas works
            tonne_per_day = ureg.Quantity(tonne_per_day, "tonne/day")
            mass_energy_density += tonne_per_day / total_mass_rate * LHV / molecular_weight.to("kg/mol")

        return mass_energy_density

    def volume_energy_density(self, stream):
        """

        :param stream:
        :return:
        """
        mass_flow_rate = stream.total_gases_rates()  # pandas.Series
        std_temp = self.field.model.const("std-temperature").to("kelvin").m
        std_press = self.field.model.const("std-pressure").to("Pa").m
        volume_energy_density = ureg.Quantity(0, "Btu/ft**3")
        for component, tonne_per_day in mass_flow_rate.items():
            if tonne_per_day == 0:
                continue
            LHV = self.dict_chemical[component].LHV
            if LHV < 0:
                LHV = -LHV
            LHV = ureg.Quantity(LHV, "joule/mol")
            LHV = LHV.to("Btu/mol")
            molecular_weight = ureg.Quantity(self.dict_chemical[component].MW, "g/mol")
            density = ureg.Quantity(self.dict_chemical[component].rho("g", std_temp, std_press), "kg/m**3")
            density = density.to("g/ft**3")
            molar_fraction = self.component_molar_fraction(component, stream)
            volume_energy_density += molar_fraction * density * LHV / molecular_weight

        return volume_energy_density



