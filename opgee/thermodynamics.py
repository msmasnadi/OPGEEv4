import pandas as pd

from opgee.core import OpgeeObject
import math
from thermosteam import Chemical, Mixture
from opgee.stream import PHASE_LIQUID, Stream, PHASE_GAS, PHASE_SOLID
from opgee import ureg
from pandas import Series


def _get_dict_chemical():
    """

    :return: a dictionary which has key of the (str) compo
    """
    carbon_number = [f'C{n + 1}' for n in range(Stream.max_carbon_number)]
    saturated_hydrocarbon = ["CH4"] + [f'C_{n + 1}H_{2 * n + 4}' for n in range(1, Stream.max_carbon_number)]
    saturated_hydrocarbon[5] = "Hexane"
    carbon_number_to_molecule = {carbon_number[i]: saturated_hydrocarbon[i] for i in range(len(carbon_number))}
    dict_chemical = {name: Chemical(carbon_number_to_molecule[name]) for name in carbon_number}
    non_hydrocarbon_gases = ["N2", "O2", "CO2", "H2O", "CO2", "H2", "H2S", "SO2"]
    dict_non_hydrocarbon = {name: Chemical(name) for name in non_hydrocarbon_gases}
    dict_chemical.update(dict_non_hydrocarbon)
    return dict_chemical


_dict_chemical = _get_dict_chemical()


def mol_weight(component, with_units=True):
    """
    Return the molecular weight of a Stream `component` (chemical)
    :param component: (str) the name of a Stream `component`
    :return: (Quantity) molecular weight
    """
    mol_weight = _dict_chemical[component].MW
    if with_units:
        mol_weight = ureg.Quantity(mol_weight, "g/mol")

    return mol_weight


def rho(component, temperature, pressure, phase):
    """
    Return the density at the given `temperature`, `pressure`, and `phase`
    for chemical `component`.

    :param component: (str) the name of a chemical
    :param temperature:
    :param pressure:
    :param phase:
    :return:
    """
    temperature = temperature.to("kelvin").m
    pressure = pressure.to("Pa").m
    phases = {PHASE_GAS: "g", PHASE_LIQUID: "l", PHASE_SOLID: "s"}

    rho = _dict_chemical[component].rho(phases[phase], temperature, pressure)
    return ureg.Quantity(rho, "kg/m**3")


def LHV(component, with_units=True):
    """

    :param component:
    :return: (float) low heat value (unit = joule/mol)
    """
    lhv = _dict_chemical[component].LHV
    if with_units:
        lhv = ureg.Quantity(abs(lhv), "joule/mol")

    return lhv


class Air(OpgeeObject):
    """
    The Air class represents the wet air and dry air chemical properties such as molar weights, density, etc.
    The wet air and dry air composition are given. The molecular weight is in unit g/mol and density is in unit
    kg/m3.
    """

    def __init__(self, field, composition):
        """

        :param field:
        :param composition:
        """
        self.composition = composition
        self.field = field
        self.components = [name for name, fraction in self.composition]
        self.mol_fraction = [fraction for name, fraction in self.composition]
        self.mixture = Mixture.from_chemicals(self.components)

    def mol_weight(self):
        mol_weight = self.mixture.MW(self.mol_fraction)
        return ureg.Quantity(mol_weight, "g/mol")

    def density(self):
        """

        :return: (float) dry air density (unit = kg/m3)
        """
        std_temp = self.field.model.const("std-temperature").to("kelvin")
        std_press = self.field.model.const("std-pressure").to("Pa")
        rho = self.mixture.rho("g", self.mol_fraction, std_temp.m, std_press.m)
        return ureg.Quantity(rho, "kg/m**3")


class WetAir(Air):
    """
    WetAir class represents the composition of wet air.
    The composition is N2 = 0.774394, O2 = 0.20531, CO2 = 0.000294, H2O = 0.02
    """

    def __init__(self, field):
        """

        :param field:
        """
        composition = [("N2", 0.774396),
                       ("O2", 0.20531),
                       ("CO2", 0.000294),
                       ("H2O", 0.02)]
        super().__init__(field, composition)


class DryAir(Air):
    """
    DryAir class represents the composition of dry air.
    The composition is N2 = 0.79, O2 = 0.21
    """

    def __init__(self, field):
        """

        :param field:
        """
        composition = [("N2", 0.79),
                       ("O2", 0.21)]
        super().__init__(field, composition)


class AbstractSubstance(OpgeeObject):
    """
    OilGasWater class contains Oil, Gas and Water class
    """

    def __init__(self, field):
        """

        :param field:
        """
        self.res_temp = field.attr("res_temp")
        self.res_press = field.attr("res_press")
        self.field = field

        self.dry_air = DryAir(field)
        self.wet_air = WetAir(field)
        self.wet_air_MW = self.wet_air.mol_weight()
        self.dry_air_MW = self.dry_air.mol_weight()

        self.std_temp = self.std_press = None

        components = list(_dict_chemical.keys())
        self.component_MW = pd.Series({name: mol_weight(name, with_units=False) for name in components},
                                      dtype="pint[g/mole]")
        self.component_LHV = pd.Series({name: LHV(name, with_units=False) for name in components},
                                       dtype="pint[joule/mole]")

    def _after_init(self):
        """

        :return:
        """
        self.std_temp = self.field.model.const("std-temperature")
        self.std_press = self.field.model.const("std-pressure")


class Oil(AbstractSubstance):
    """

    """
    # Bubblepoint pressure constants
    pbub_a1 = 5.527215
    pbub_a2 = 0.783716
    pbub_a3 = 1.841408

    def __init__(self, field):
        """

        :param field:
        """

        """

        :param API: (float) API gravity
        :param gas_comp: (panda.Series, float) Produced gas composition; unit = fraction
        :param gas_oil_ratio: (float) The ratio of the volume of gas that comes out of solution to the volume of oil at 
        standard conditions; unit = fraction
        :param reservoir_temperature: (float) average reservoir temperature; unit = F
        :param reservoir_pressure: (float) average reservoir pressure; unit = psia
        """
        super().__init__(field)

        self.API = API = field.attr("API")
        self.gas_comp = field.attrs_with_prefix('gas_comp_')
        self.gas_oil_ratio = field.attr('GOR')
        self.oil_specific_gravity = ureg.Quantity(141.5 / (131.5 + API.m), "frac")
        self.gas_specific_gravity = self._gas_specific_gravity()

    def _gas_specific_gravity(self):
        """
        Gas specific gravity is defined as the ratio of the molecular weight (MW) of the gas
        to the MW of wet air

        :return: (float) gas specific gravity (unit = fraction)
        """
        gas_comp = self.gas_comp
        gas_SG = (gas_comp * self.component_MW[gas_comp.index]).sum()

        gas_SG = gas_SG / self.dry_air_MW
        return gas_SG

    @staticmethod
    def bubble_point_solution_GOR(gas_oil_ratio):
        """
        R_sb = 1.1618 * R_sp
        R_Sb is GOR at bubblepoint, R_sp is GOR at separator
        Valco and McCain (2002) give a means to estimate
        the bubble point gas-oil ratio from the separator gas oil ratio.
        Since OPGEE takes separator gas oil ratio as an input, we use this

        :return:(float) GOR at bubblepoint (unit = scf/bbl)
        """
        result = gas_oil_ratio * 1.1618
        return result

    def reservoir_solution_GOR(self):
        """
        The solution gas oil ratio (GOR) at resevoir condition is
        the minimum of empirical correlation and bubblepoint GOR

        :return: (float) solution gas oil ratio at resevoir condition (unit = scf/bbl)
        """
        oil_SG = self.oil_specific_gravity
        res_temperature = self.res_temp.to("rankine").m
        res_pressure = self.res_press.m
        gas_SG = self.gas_specific_gravity
        gor_bubble = self.bubble_point_solution_GOR(self.gas_oil_ratio)

        result = min([
            res_pressure ** (1 / self.pbub_a2) *
            oil_SG ** (-self.pbub_a1 / self.pbub_a2) *
            math.exp(self.pbub_a3 / self.pbub_a2 * gas_SG * oil_SG) /
            (res_temperature * gas_SG),
            gor_bubble])
        result = ureg.Quantity(result, "scf/bbl_oil")
        return result

    def bubble_point_pressure(self, stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio):
        """

        :param stream:
        :param oil_specific_gravity:
        :param gas_specific_gravity:
        :param gas_oil_ratio:
        :return:
        """
        oil_SG = oil_specific_gravity.m
        temperature = stream.temperature.to("rankine").m

        gas_SG = gas_specific_gravity.to("frac").m
        gor_bubble = self.bubble_point_solution_GOR(gas_oil_ratio).m

        result = (oil_SG ** self.pbub_a1 *
                  (gas_SG * gor_bubble * temperature) ** self.pbub_a2 *
                  math.exp(-self.pbub_a3 * gas_SG * oil_SG))
        result = ureg.Quantity(result, "psia")
        return result

    def solution_gas_oil_ratio(self, stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio):
        """
        The solution gas-oil ratio (GOR) is a general term for the amount of gas dissolved in the oil

        :return: (float) solution gas oil ratio (unit = scf/bbl)
        """
        oil_SG = oil_specific_gravity.m
        stream_temp = stream.temperature.to("rankine").m
        stream_press = stream.pressure.m

        gas_SG = gas_specific_gravity.to("frac").m
        gor_bubble = self.bubble_point_solution_GOR(gas_oil_ratio)

        result = min(math.pow(stream_press, 1 / self.pbub_a2) *
                     math.pow(oil_SG, -self.pbub_a1 / self.pbub_a2) *
                     math.exp(self.pbub_a3 / self.pbub_a2 * gas_SG * oil_SG) *
                     1 / (stream_temp * gas_SG),
                     gor_bubble)
        result = ureg.Quantity(result, "scf/bbl_oil")
        return result

    def saturated_formation_volume_factor(self, stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio):
        """
        the formation volume factor is defined as the ratio of the volume of oil (plus the gas in solution)
        at the prevailing reservoir temperature and pressure to the volume of oil at standard conditions

        :return: (float) saturated formation volume factor (unit = fraction)
        """
        oil_SG = oil_specific_gravity.m
        stream_temp = stream.temperature.m

        gas_SG = gas_specific_gravity.to("frac").m
        solution_gor = self.solution_gas_oil_ratio(stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio).m

        result = (1 + 0.000000525 * solution_gor * (stream_temp - 60) +
                  0.000181 * solution_gor / oil_SG + 0.000449 * (stream_temp - 60) / oil_SG +
                  0.000206 * solution_gor * gas_SG / oil_SG)
        result = ureg.Quantity(result, "frac")
        return result

    def unsat_formation_volume_factor(self,
                                      stream,
                                      oil_specific_gravity,
                                      gas_specific_gravity,
                                      gas_oil_ratio):
        """
        the formation volume factor is defined as the ratio of the volume of oil (plus the gas in solution)
        at the prevailing reservoir temperature and pressure to the volume of oil at standard conditions

        :return: (float) unsaturated formation volume factor (unit = fraction)
        """
        res_stream = Stream("test_stream", temperature=self.res_temp, pressure=self.res_press)
        bubble_oil_FVF = self.saturated_formation_volume_factor(res_stream,
                                                                self.oil_specific_gravity,
                                                                self.gas_specific_gravity,
                                                                self.gas_oil_ratio).m

        p_bubblepoint = self.bubble_point_pressure(stream,
                                                   oil_specific_gravity,
                                                   gas_specific_gravity,
                                                   gas_oil_ratio).m
        isothermal_compressibility = self.isothermal_compressibility(oil_specific_gravity).m
        stream_press = stream.pressure.m

        result = bubble_oil_FVF * math.exp(isothermal_compressibility * (p_bubblepoint - stream_press))
        result = ureg.Quantity(result, "frac")
        return result

    def isothermal_compressibility_X(self, stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio):
        """
        Isothermal compressibility is the change in volume of a system as the pressure changes
        while temperature remains constant.

        :return:
        """
        # Isothermal compressibility constants
        iso_comp_a1 = -0.000013668
        iso_comp_a2 = -0.00000001925682
        iso_comp_a3 = 0.02408026
        iso_comp_a4 = -0.0000000926091

        solution_gor = self.solution_gas_oil_ratio(stream,
                                                   oil_specific_gravity,
                                                   gas_specific_gravity,
                                                   gas_oil_ratio).m
        gas_SG = gas_specific_gravity.to("frac").m
        stream_temp = stream.temperature.to("rankine").m

        result = max((iso_comp_a1 * solution_gor + iso_comp_a2 * solution_gor ** 2 +
                      iso_comp_a3 * gas_SG + iso_comp_a4 * stream_temp ** 2), 0.0)
        result = ureg.Quantity(result, "pa**-1")
        return result

    @staticmethod
    def isothermal_compressibility(oil_specific_gravity):
        """
        Regression from ...

        :return:
        """
        oil_SG = oil_specific_gravity.m
        result = (55.233 - 60.588 * oil_SG) / 1e6
        result = ureg.Quantity(result, "pa**-1")
        return result

    def formation_volume_factor(self,
                                stream,
                                oil_specific_gravity,
                                gas_specific_gravity,
                                gas_oil_ratio):
        """
        the formation volume factor is defined as the ratio of the volume of oil (plus the gas in solution)
        at the prevailing reservoir temperature and pressure to the volume of oil at standard conditions

        :return:(float) final formation volume factor (unit = fraction)
        """
        p_bubblepoint = self.bubble_point_pressure(stream,
                                                   oil_specific_gravity,
                                                   gas_specific_gravity,
                                                   gas_oil_ratio)

        result = (self.saturated_formation_volume_factor(stream,
                                                         oil_specific_gravity,
                                                         gas_specific_gravity,
                                                         gas_oil_ratio)
                  if stream.pressure < p_bubblepoint else
                  self.unsat_formation_volume_factor(stream,
                                                     oil_specific_gravity,
                                                     gas_specific_gravity,
                                                     gas_oil_ratio))
        return result

    def density(self, stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio):
        """

        :param stream:
        :param oil_specific_gravity:
        :param gas_specific_gravity:
        :param gas_oil_ratio:
        :return:
        """
        oil_SG = oil_specific_gravity.m

        gas_SG = gas_specific_gravity.to("frac").m
        solution_gor = self.solution_gas_oil_ratio(stream,
                                                   oil_specific_gravity,
                                                   gas_specific_gravity,
                                                   gas_oil_ratio).m
        volume_factor = self.formation_volume_factor(stream,
                                                     oil_specific_gravity,
                                                     gas_specific_gravity,
                                                     gas_oil_ratio).m

        result = (62.42796 * oil_SG + 0.0136 * gas_SG * solution_gor) / volume_factor
        return ureg.Quantity(result, "lb/ft**3")

    def volume_flow_rate(self, stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio):
        """

        :param stream:
        :param oil_specific_gravity:
        :param gas_specific_gravity:
        :param gas_oil_ratio:
        :return:(float) oil volume flow rate (unit = bbl/day)
        """

        mass_flow_rate = stream.hydrocarbon_rate(PHASE_LIQUID)
        density = self.density(stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio)

        volume_flow_rate = (mass_flow_rate / density).to("bbl_oil/day")
        return volume_flow_rate

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

        result = (oil_LHV_a1 + oil_LHV_a2 * API - oil_LHV_a3 * API ** 2 - oil_LHV_a4 * API ** 3)
        return ureg.Quantity(result, "british_thermal_unit/lb")

    def volume_energy_density(self, stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio):
        """

        :return:(float) volume energy density (unit = mmBtu/bbl)
        """
        mass_energy_density = self.mass_energy_density()
        density = self.density(stream,
                               oil_specific_gravity,
                               gas_specific_gravity,
                               gas_oil_ratio).to("lb/bbl_oil")

        result = mass_energy_density * density
        return result.to("mmBtu/bbl_oil")

    def energy_flow_rate(self, stream):
        """

        :return:(float) energy flow rate (unit = mmBtu/day)
        """
        mass_flow_rate = stream.hydrocarbon_rate(PHASE_LIQUID)
        mass_flow_rate = mass_flow_rate.to("lb/day")
        mass_energy_density = self.mass_energy_density()

        result = mass_energy_density * mass_flow_rate
        return result.to("mmbtu/day")


class Gas(AbstractSubstance):
    """

    """

    def __init__(self, field):
        """

        :param field:
        """
        super().__init__(field)

    def total_molar_flow_rate(self, stream):
        """

        :param stream:
        :return: (float) total molar flow rate (unit = mol/day)
        """
        mass_flow_rate = stream.total_gases_rates()  # pandas.Series
        total_molar_flow_rate = (mass_flow_rate / self.component_MW).sum().to("mol/day")

        return total_molar_flow_rate

    # TODO: change all loops that call this to use component_molar_fractions() instead and use operations on Series objects.
    def component_molar_fraction(self, name, stream):
        """

        :param name: (str) component name
        :param stream:
        :return:
        """
        total_molar_flow_rate = self.total_molar_flow_rate(stream)
        mass_flow_rate = stream.gas_flow_rate(name)
        molecular_weight = mol_weight(name)
        molar_flow_rate = mass_flow_rate.to("g/day") / molecular_weight

        result = molar_flow_rate / total_molar_flow_rate
        return result.to("frac")

    # TODO: this gets the fractions in a series, all at once. The units are weird, but
    # TODO: when converted to base units, they are correct numerically.
    def component_molar_fractions(self, stream):
        """

        :param stream:
        :return:
        """
        total_molar_flow_rate = self.total_molar_flow_rate(stream)
        gas_flow_rates = stream.components.query("gas > 0.0").gas

        molar_flow_rate = gas_flow_rates / self.component_MW[gas_flow_rates.index]

        result = molar_flow_rate / total_molar_flow_rate
        result = pd.Series(result, dtype="pint[fraction]")  # convert units
        return result

    def specific_gravity(self, stream):
        """

        :param stream:
        :return:
        """
        mol_fracs = self.component_molar_fractions(stream)
        sg = (mol_fracs * self.component_MW[mol_fracs.index]).sum()
        sg = sg / self.dry_air_MW
        return sg

    @staticmethod
    def ratio_of_specific_heat(stream):
        """

        :param stream:
        :return:
        """
        mass_flow_rate = stream.total_gases_rates()  # pandas.Series
        universal_gas_constants = ureg.Quantity(8.31446261815324, "joule/mol/kelvin")  # J/mol/K
        specific_heat_press = 0
        specific_heat_volm = 0
        for component, tonne_per_day in mass_flow_rate.items():
            molecular_weight = mol_weight(component)
            gas_constant = universal_gas_constants / molecular_weight
            Cp = ureg.Quantity(_dict_chemical[component].Cp(phase='g', T=298.15), "joule/g/kelvin")
            Cv = Cp - gas_constant
            specific_heat_press += tonne_per_day.to("g/day") * Cp
            specific_heat_volm += tonne_per_day.to("g/day") * Cv

        ratio_of_specific_heat = specific_heat_press / specific_heat_volm
        return ratio_of_specific_heat.to("frac")

    def uncorrected_pseudocritical_temperature_and_pressure(self, stream):
        """

        :param stream:
        :return:(float) pandas.Series
        """
        mass_flow_rate = stream.total_gases_rates()  # pandas.Series
        temp1 = 0
        temp2 = 0
        temp3 = 0
        for component, tonne_per_day in mass_flow_rate.items():
            if tonne_per_day == 0:
                continue
            molar_fraction = self.component_molar_fraction(component, stream).m

            chemical = _dict_chemical[component]
            critical_temperature = ureg.Quantity(chemical.Tc, "kelvin").to("rankine")
            critical_temperature = critical_temperature.m
            critical_pressure = ureg.Quantity(chemical.Pc, "Pa").to("psia")
            critical_pressure = critical_pressure.m

            temp1 += molar_fraction * critical_temperature / critical_pressure ** 0.5
            temp2 += molar_fraction * critical_temperature / critical_pressure
            temp3 += molar_fraction * (critical_temperature / critical_pressure) ** 0.5
        temp1 = temp1 ** 2
        temp2 = 1 / 3 * temp2
        temp3 = 2 / 3 * temp3 ** 2
        temperature = ureg.Quantity(temp1 / (temp2 + temp3), "rankine")
        pressure = ureg.Quantity(temp1 / (temp2 + temp3) ** 2, "psia")
        return Series(data=[temperature, pressure], index=["temperature", "pressure"])

    def corrected_pseudocritical_temperature(self, stream):
        """

        :param stream:
        :return: (float) corrected pseudocritical temperature (unit = rankine)
        """
        uncorr_pseudocritical_temp = self.uncorrected_pseudocritical_temperature_and_pressure(stream)["temperature"].m
        molar_frac_O2 = self.component_molar_fraction("O2", stream).m
        molar_frac_H2S = self.component_molar_fraction("H2S", stream).m
        result = (uncorr_pseudocritical_temp -
                  120 * ((molar_frac_O2 + molar_frac_H2S) ** 0.9 - (molar_frac_O2 + molar_frac_H2S) ** 1.6) +
                  15 * (molar_frac_H2S ** 0.5 - molar_frac_H2S ** 4)
                  )
        return ureg.Quantity(result, "rankine")

    def corrected_pseudocritical_pressure(self, stream):
        """

        :param stream:
        :return:
        """
        uncorr_pseudocritical_temp = self.uncorrected_pseudocritical_temperature_and_pressure(stream)["temperature"]
        uncorr_pseudocritical_press = self.uncorrected_pseudocritical_temperature_and_pressure(stream)["pressure"]
        corr_pseudocritical_temp = self.corrected_pseudocritical_temperature(stream)
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
        corr_pseudocritical_temp = self.corrected_pseudocritical_temperature(stream)
        result = stream.temperature.to("rankine") / corr_pseudocritical_temp

        return result.to("frac")

    def reduced_pressure(self, stream):
        """

        :param stream:
        :return:
        """
        corr_pseudocritical_press = self.corrected_pseudocritical_pressure(stream)
        result = stream.pressure / corr_pseudocritical_press

        return result.to("frac")

    @staticmethod
    def Z_factor(reduced_temperature, reduced_pressure):
        """

        :param reduced_temperature:
        :param reduced_pressure:
        :return:(float) gas z_factor (unit = frac)
        """
        reduced_temp = reduced_temperature.m
        reduced_press = reduced_pressure.m

        z_factor_A = 1.39 * (reduced_temp - 0.92) ** 0.5 - 0.36 * reduced_temp - 0.101
        z_factor_B = (reduced_press * (0.62 - 0.23 * reduced_temp) +
                      reduced_press ** 2 * (0.066 / (reduced_temp - 0.86) - 0.037) +
                      0.32 * reduced_temp ** 6 / (10 ** (9 * reduced_temp - 9)))
        z_factor_C = 0.132 - 0.32 * math.log10(reduced_temp)
        z_factor_D = 10 ** (0.3106 - 0.49 * reduced_temp + 0.1824 * reduced_temp ** 2)
        z_factor = max((z_factor_A + (1 - z_factor_A) * math.exp(-1 * z_factor_B)
                        + z_factor_C * reduced_press ** z_factor_D), 0.05)
        z_factor = ureg.Quantity(z_factor, "frac")

        return z_factor

    def volume_factor(self, stream):
        """

        :param stream:
        :return:
        """

        z_factor = self.Z_factor(self.reduced_temperature(stream), self.reduced_pressure(stream))
        temp = stream.temperature.to("rankine")
        amb_temp = self.field.model.const("std-temperature").to("rankine")
        amb_press = self.field.model.const("std-pressure")

        result = amb_press * z_factor * temp / (stream.pressure * amb_temp)
        return result.to("frac")

    def density(self, stream):
        """

        :param stream:
        :return: (float) gas density (unit = tonne/m3)
        """
        volume_factor = self.volume_factor(stream)
        specific_gravity = self.specific_gravity(stream)
        air_density_stp = self.dry_air.density()

        return air_density_stp.to("tonne/m**3") * specific_gravity / volume_factor

    def viscosity(self, stream):
        """
        Calculate natural gas viscosity using Lee et al.(1966) correlation

        :param stream:
        :return:(float) natural gas viscosity (unit = cP)
        """
        gas_stream_molar_weight = self.molar_weight(stream).m
        gas_density = self.density(stream).to("lb/ft**3").m
        temp = stream.temperature.to("rankine").m

        factor_K = (9.4 + 0.02 * gas_stream_molar_weight) * temp ** 1.5 / (209 + 19 * gas_stream_molar_weight + temp)
        factor_X = 3.5 + 986 / temp + 0.01 * gas_stream_molar_weight
        factor_Y = 2.4 - 0.2 * factor_X

        viscosity = 1.10e-4 * factor_K * math.exp(factor_X * (gas_density / 62.4) ** factor_Y)
        return ureg.Quantity(viscosity, "centipoise")

    def molar_weight(self, stream):
        """

        :param stream:
        :return:
        """
        mol_fracs = self.component_molar_fractions(stream)
        molar_weight = (self.component_MW[mol_fracs.index] * mol_fracs).sum()

        return molar_weight.to("g/mol")

    def volume_flow_rate(self, stream):
        """

        :param stream:
        :return: Gas volume flow rate (unit = m3/day)
        """
        total_mass_rate = stream.total_gas_rate()
        density = self.density(stream)

        volume_flow_rate = total_mass_rate / density
        return volume_flow_rate

    @staticmethod
    def mass_energy_density(stream):
        """

        :param stream:
        :return: (float) gas mass energy density (unit = MJ/kg)
        """
        mass_flow_rate = stream.total_gases_rates()  # pandas.Series
        total_mass_rate = stream.total_gas_rate()
        mass_energy_density = ureg.Quantity(0.0, "MJ/kg")
        for component, tonne_per_day in mass_flow_rate.items():
            if tonne_per_day == 0:
                continue
            lhv = LHV(component).to("MJ/mol")
            molecular_weight = mol_weight(component)
            mass_energy_density += tonne_per_day / total_mass_rate * lhv / molecular_weight.to("kg/mol")

        return mass_energy_density

    def volume_energy_density(self, stream):
        """

        :param stream:
        :return:(float) gas volume energy density (unit = btu/scf)
        """
        mass_flow_rate = stream.total_gases_rates()  # pandas.Series
        std_temp = self.field.model.const("std-temperature")
        std_press = self.field.model.const("std-pressure")
        volume_energy_density = ureg.Quantity(0.0, "Btu/ft**3")
        for component, tonne_per_day in mass_flow_rate.items():
            if tonne_per_day == 0:
                continue
            lhv = LHV(component)
            molecular_weight = mol_weight(component)
            density = rho(component, std_temp, std_press, PHASE_GAS)
            molar_fraction = self.component_molar_fraction(component, stream)
            volume_energy_density += molar_fraction * density * lhv / molecular_weight

        return volume_energy_density.to("Btu/ft**3")

    def energy_flow_rate(self, stream):
        """

        :param stream:
        :return: (float) energy flow rate (unit = mmBtu/day)
        """
        total_mass_flow_rate = stream.total_gas_rate()
        mass_energy_density = self.mass_energy_density(stream)
        energy_flow_rate = total_mass_flow_rate.to("kg/day") * mass_energy_density.to("mmBtu/kg")

        return energy_flow_rate


class Water(AbstractSubstance):
    """
    water class includes the method to calculate water density, water volume flow rate, etc.
    """

    def __init__(self, field):
        super().__init__(field)
        self.TDS = field.attr("total_dissolved_solids")  # mg/L
        # TODO: this can be improved by adding ions in the H2O in the solution
        self.specific_gravity = ureg.Quantity(1 + self.TDS.m * 0.695 * 1e-6, "frac")

    def density(self):
        """
        water density

        :return: (float) water density (unit = kg/m3)
        """

        specifc_gravity = self.specific_gravity
        water_density_STP = rho("H2O", self.std_temp, self.std_press, PHASE_LIQUID)
        density = specifc_gravity * water_density_STP

        return density.to("kg/m**3")

    def volume_flow_rate(self, stream):
        """

        :param stream:
        :return: (float) water volume flow rate (unit = bbl_water/d)
        """
        mass_rate = stream.flow_rate("H2O", PHASE_LIQUID)
        density = self.density()

        volume_flow_rate = (mass_rate / density).to("bbl_water/day")
        return volume_flow_rate
