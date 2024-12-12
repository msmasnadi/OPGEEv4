#
# Thermodynamic information classes
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import math

import pandas as pd
import numpy as np
import pint
from pyXSteam.XSteam import XSteam
from thermosteam import Chemical, IdealMixture

from . import ureg
from .core import OpgeeObject, STP, TemperaturePressure
from .error import ModelValidationError
from .stream import PHASE_LIQUID, Stream, PHASE_GAS, PHASE_SOLID


class ChemicalInfo(OpgeeObject):
    instance = None

    def __init__(self):
        dict_non_hydrocarbon = {name: Chemical(name) for name in Stream.non_hydrocarbon_gases}
        series = Stream.pubchem_cid_df.PubChem
        self._chemical_dict = chemical_dict = {name : Chemical(f"PubChem={num}") for name, num in series.items()}
        chemical_dict.update(dict_non_hydrocarbon)
        self._mol_weights = pd.Series({name: chemical.MW for name, chemical in chemical_dict.items()},
                                      dtype="pint[g/mole]")

    @classmethod
    def get_instance(cls):
        if cls.instance is None:
            cls.instance = cls()

        return cls.instance

    @classmethod
    def chemical(cls, component_name):
        obj = cls.get_instance()
        return obj._chemical_dict[component_name]

    @classmethod
    def mol_weight(cls, component, with_units=True):
        obj = cls.get_instance()
        mw = obj._mol_weights.get(component)
        return mw if with_units else mw.m

    @classmethod
    def mol_weights(cls):
        obj = cls.get_instance()
        return obj._mol_weights

    @classmethod
    def names(cls):
        obj = cls.get_instance()
        return list(obj._mol_weights.keys())


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

    chemical = ChemicalInfo.chemical(component)
    curr_phase = chemical.get_phase(temperature, pressure)
    if curr_phase == phases[phase]:
        result = chemical.rho(phases[phase], temperature, pressure)
    else:
        result = chemical.rho(curr_phase, temperature, pressure)
    return ureg.Quantity(result, "kg/m**3")


def heating_value(component, use_LHV=True, with_units=True):
    """
    Return the lower or higher heating value for the given component,
    with or without Pint units.

    :param component: (str) the name of a stream component
    :param use_LHV: (bool) whether to use LHV, else use HHV
    :param with_units: (bool) whether to return a pint.Quantity()
    :return: (float or pint.Quantity) lower or higher heating value (unit = joule/mol if with_units)
    """
    chemical = ChemicalInfo.chemical(component)

    hv = chemical.LHV if use_LHV else chemical.HHV
    hv = abs(hv) if hv is not None else 0

    if with_units:
        hv = ureg.Quantity(hv, "joule/mol")

    return hv


def LHV(component, with_units=True):
    """
    Return the lower heating value for the given component, with or without Pint units.

    :param component: (str) the name of a stream component
    :param with_units: (bool) whether to return a pint.Quantity()

    :return: (float) lower heating value (unit = joule/mol)
    """
    return heating_value(component, with_units=with_units)


def Cp(component, kelvin, with_units=True):
    """

    :param kelvin: unit in Kelvin
    :param component:
    :param with_units: (bool) whether to return a pint.Quantity()

    :return: (float) specific heat in standard condition (unit = joule/g/kelvin)
    """
    chemical = ChemicalInfo.chemical(component)
    cp = chemical.Cp(phase='g', T=kelvin)
    if with_units:
        cp = ureg.Quantity(cp, "joule/g/kelvin")

    return cp


# TODO: this is used in only one place, with phase=PHASE_GAS and with_units=False,
#       so this could be simplified in that usage to:
#       def gas_enthalpy(component, temp_K):
#           chemical = ChemicalInfo.chemical(component)
#           return chemical.H('g', T=temp_K)
def Enthalpy(component, kelvin, phase=PHASE_GAS, with_units=True):
    """
    calculate enthalpy of component given temperature and phase

    :param phase:
    :param component:
    :param kelvin:
    :param with_units: (bool) whether to return a pint.Quantity()

    :return: (float) enthalpy (unit = joule/mole)
    """
    if isinstance(kelvin, ureg.Quantity):
        kelvin = kelvin.to("kelvin")
        kelvin = kelvin.m

    chemical = ChemicalInfo.chemical(component)

    phase_letter = "g" if phase == PHASE_GAS else "l"
    H = chemical.H(phase=phase_letter, T=kelvin)

    if with_units:
        H = ureg.Quantity(H, "joule/mol")

    return H


# TODO called twice. Simplify?
def Tsat(component, Psat, with_units=True):
    """

    :param Psat: saturated pressure (unit in Pa)
    :param component:
    :param with_units: (bool) whether to return a pint.Quantity()

    :return:
    """
    chemical = ChemicalInfo.chemical(component)
    Psat = min(chemical.Pc * 0.99, Psat)
    result = chemical.Tsat(Psat)

    if with_units:
        result = ureg.Quantity(result, "kelvin")

    return result


# TODO only used once. Simplify?
def Tc(component, with_units=True):
    """

    :param component:
    :param with_units: (bool) whether to return a pint.Quantity()

    :return: (float) critical temperature (unit = kelvin)
    """
    chemical = ChemicalInfo.chemical(component)
    tc = chemical.Tc

    if with_units:
        tc = ureg.Quantity(tc, "kelvin")

    return tc


# TODO only used once. Simplify?
def Pc(component, with_units=True):
    """

    :param component:
    :param with_units: (bool) whether to return a pint.Quantity()

    :return:(pint.Quantity or float) critical pressure, with unit="Pa" if ``with_units``.
    """
    chemical = ChemicalInfo.chemical(component)
    pc = chemical.Pc

    if with_units:
        pc = ureg.Quantity(pc, "Pa")

    return pc


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
        self.mol_fraction = mol_fraction = [fraction for name, fraction in self.composition]
        self.mixture = mixture = IdealMixture.from_chemicals(self.components)
        self.mol_weight = ureg.Quantity(mixture.MW(mol_fraction), "g/mol")

    def density(self):
        """

        :return: (float) dry air density (unit = kg/m3)
        """
        std_temp = STP.T.to("kelvin")
        std_press = STP.P.to("Pa")
        result = self.mixture.rho("g", self.mol_fraction, std_temp.m, std_press.m)
        return ureg.Quantity(result, "kg/m**3")


# Deprecated? Currently unused.
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
    The composition is obtained from https://www.engineeringtoolbox.com/air-composition-d_212.html
    """

    def __init__(self, field):
        """

        :param field:
        """
        composition = [("Nitrogen", 0.78084),
                       ("Oxygen", 0.20946),
                       ("Argon", 0.00934),
                       ("Carbon dioxide", 0.000412),
                       ("Neon", 0.00001818),
                       ("Helium", 0.00000524),
                       ("Methane", 0.00000179),
                       ("Krypton", 0.0000010),
                       ("Hydrogen", 0.0000005),
                       ("Xenon", 0.00000009)]

        super().__init__(field, composition)


class AbstractSubstance(OpgeeObject):
    """
    AbstractSubstance class is superclass of Oil, Gas and Water
    """

    def __init__(self, field):
        """

        :param field:
        """
        self.res_tp = TemperaturePressure(field.attr("res_temp"), field.attr("res_press"))

        self.model = field.model

        self.dry_air = DryAir(field)


        # TODO: refactor this. Currently each subclass of AbstractSubstance calls this __init__
        #  method and stores redundant copies of all the variables below. Make these class vars
        #  instead so they are computed and stored only once.
        self.component_MW = ChemicalInfo.mol_weights()
        components = self.component_MW.index

        self.component_LHV_molar = pd.Series(
            {name: heating_value(name, with_units=False) for name in components},
            dtype="pint[joule/mole]")
        self.component_LHV_mass = self.component_LHV_molar / self.component_MW  # joule/gram

        self.component_HHV_molar = pd.Series(
            {name: heating_value(name, use_LHV=False, with_units=False) for name in components},
            dtype="pint[joule/mole]")
        self.component_HHV_mass = self.component_LHV_molar / self.component_MW  # joule/gram

        self.component_Cp_STP = pd.Series({name: Cp(name, 288.706, with_units=False) for name in components},
                                          dtype="pint[joule/g/kelvin]")
        self.component_Tc = pd.Series({name: Tc(name, with_units=False) for name in components},
                                      dtype="pint[kelvin]")
        self.component_Pc = pd.Series({name: Pc(name, with_units=False) for name in components},
                                      dtype="pint[Pa]")
        self.component_gas_rho_STP = pd.Series({name: rho(name, field.stp.T, field.stp.P, PHASE_GAS)
                                                for name in components}, dtype="pint[kg/m**3]")

        self.steam_table = XSteam(XSteam.UNIT_SYSTEM_FLS)


class Oil(AbstractSubstance):
    """
    Describes thermodynamic properties of crude oil.
    """

    # Bubblepoint pressure constants
    pbub_a1 = 5.527215
    pbub_a2 = 0.783716
    pbub_a3 = 1.841408

    def __init__(self, field):
        """
        Store common parameters describing crude oil.

        :param field: (opgee.Field) the `Field` of interest, used to get values of various field attributes.
        """
        super().__init__(field)

        self.API = API = field.attr("API")
        self.oil_LHV_mass = self.mass_energy_density()
        self.component_LHV_mass['oil'] = self.oil_LHV_mass.to("joule/gram")
        self.gas_comp = field.attrs_with_prefix('gas_comp_')
        self.gas_oil_ratio = field.attr('GOR')
        self.oil_specific_gravity = ureg.Quantity(141.5 / (131.5 + API.m), "frac")
        self.total_molar_weight = (self.gas_comp * self.component_MW[self.gas_comp.index]).sum()
        self.gas_specific_gravity = self._gas_specific_gravity()

        self.water = Water(field)

    # TODO: Used only once, immediately above
    def _gas_specific_gravity(self):
        """
        Gas specific gravity is defined as the ratio of the molecular weight (MW) of the gas
        to the MW of wet air

        :return: (float) gas specific gravity (unit = fraction)
        """

        gas_SG = self.total_molar_weight / self.dry_air.mol_weight
        return gas_SG.to("frac")

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

    @staticmethod
    def specific_gravity(API_grav):
        """
        Calculate specific gravity of crude oil using the API standard SG at 60C = 141.5/(API+131.5)
        :param API_grav:

        :return:
        """
        API_grav_value = API_grav.m if isinstance(API_grav, pint.Quantity) else API_grav
        result = 141.5 / (API_grav_value + 131.5)
        return ureg.Quantity(result, "frac")

    @staticmethod
    def API_from_SG(SG):
        """
        Calculate API from specific gravity
        :param SG:
        :return:
        """

        SG = SG.to("frac").m if isinstance(SG, pint.Quantity) else SG
        result = 141.5 / SG - 131.5
        return ureg.Quantity(result, "degAPI")

    # TODO used only in tests
    def reservoir_solution_GOR(self):
        """
        The solution gas oil ratio (GOR) at resevoir condition is
        the minimum of empirical correlation and bubblepoint GOR

        :return: (float) solution gas oil ratio at resevoir condition (unit = scf/bbl)
        """
        oil_SG = self.oil_specific_gravity.to("frac").m

        res_T = self.res_tp.T.to("rankine").m
        res_P = self.res_tp.P.to("psia").m

        gas_SG = self.gas_specific_gravity.to("frac").m
        gor_bubble = self.bubble_point_solution_GOR(self.gas_oil_ratio).m

        empirical_res = (res_P ** (1 / self.pbub_a2) *
                         oil_SG ** (-self.pbub_a1 / self.pbub_a2) *
                         math.exp(self.pbub_a3 / self.pbub_a2 * gas_SG * oil_SG) /
                         (res_T * gas_SG))
        result = min([empirical_res, gor_bubble])
        result = ureg.Quantity(result, "scf/bbl_oil")
        return result

    def bubble_point_pressure(self, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio):
        """

        :param oil_specific_gravity:
        :param gas_specific_gravity:
        :param gas_oil_ratio:

        :return:
        """
        oil_SG = oil_specific_gravity.to("frac").m
        res_temp = self.res_tp.T.to("rankine").m

        gas_SG = gas_specific_gravity.to("frac").m
        gor_bubble = self.bubble_point_solution_GOR(gas_oil_ratio).m

        result = (oil_SG ** self.pbub_a1 *
                  (gas_SG * gor_bubble * res_temp) ** self.pbub_a2 *
                  math.exp(-self.pbub_a3 * gas_SG * oil_SG))
        result = ureg.Quantity(result, "psia")
        return result

    def solution_gas_oil_ratio(self, stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio):
        """
        The solution gas-oil ratio (GOR) is a general term for the amount of gas dissolved in the oil

        :return: (float) solution gas oil ratio (unit = scf/bbl)
        """
        oil_SG = oil_specific_gravity.to("frac").m
        stream_T = stream.tp.T.to("rankine").m
        stream_P = stream.tp.P.m

        gas_SG = gas_specific_gravity.to("frac").m
        gor_bubble = self.bubble_point_solution_GOR(gas_oil_ratio)

        result = min(math.pow(stream_P, 1 / self.pbub_a2) *
                     math.pow(oil_SG, -self.pbub_a1 / self.pbub_a2) *
                     math.exp(self.pbub_a3 / self.pbub_a2 * gas_SG * oil_SG) *
                     1 / (stream_T * gas_SG),
                     gor_bubble.m)
        result = ureg.Quantity(result, "scf/bbl_oil")
        return result

    def saturated_formation_volume_factor(self, stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio):
        """
        The formation volume factor is defined as the ratio of the volume of oil (plus the gas in solution)
        at the prevailing reservoir temperature and pressure to the volume of oil at standard conditions

        :return: (float) saturated formation volume factor (unit = fraction)
        """
        oil_SG = oil_specific_gravity.to("frac").m
        stream_T = stream.tp.T.m

        gas_SG = gas_specific_gravity.to("frac").m
        solution_gor = self.solution_gas_oil_ratio(stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio).m

        result = (1 + 0.000000525 * solution_gor * (stream_T - 60) +
                  0.000181 * solution_gor / oil_SG + 0.000449 * (stream_T - 60) / oil_SG +
                  0.000206 * solution_gor * gas_SG / oil_SG)
        result = ureg.Quantity(result, "frac")
        return result

    def unsat_formation_volume_factor(self,
                                      stream,
                                      oil_specific_gravity,
                                      gas_specific_gravity,
                                      gas_oil_ratio):
        """
        The formation volume factor is defined as the ratio of the volume of oil (plus the gas in solution)
        at the prevailing reservoir temperature and pressure to the volume of oil at standard conditions

        :return: (float) unsaturated formation volume factor (unit = fraction)
        """
        res_stream = Stream("test_stream", self.res_tp)
        bubble_oil_FVF = self.saturated_formation_volume_factor(res_stream,
                                                                self.oil_specific_gravity,
                                                                self.gas_specific_gravity,
                                                                self.gas_oil_ratio).m

        p_bubblepoint = self.bubble_point_pressure(oil_specific_gravity,
                                                   gas_specific_gravity,
                                                   gas_oil_ratio).m
        isothermal_compressibility = self.isothermal_compressibility(oil_specific_gravity).m
        stream_press = stream.tp.P.m

        result = bubble_oil_FVF * math.exp(isothermal_compressibility * (p_bubblepoint - stream_press))
        result = ureg.Quantity(result, "frac")
        return result

    # TODO: used only in tests
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
        stream_temp = stream.tp.T.to("rankine").m

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
        p_bubblepoint = self.bubble_point_pressure(oil_specific_gravity,
                                                   gas_specific_gravity,
                                                   gas_oil_ratio)

        result = (self.saturated_formation_volume_factor(stream,
                                                         oil_specific_gravity,
                                                         gas_specific_gravity,
                                                         gas_oil_ratio)
                  if stream.tp.P < p_bubblepoint else
                  self.unsat_formation_volume_factor(stream,
                                                     oil_specific_gravity,
                                                     gas_specific_gravity,
                                                     gas_oil_ratio))
        return result

    def density(self, stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio):
        """
        Calculate the density of a mixture of oil and gas in a stream.

        :param stream: The stream containing the oil and gas mixture
        :param oil_specific_gravity: The specific gravity of the oil component
        :param gas_specific_gravity: The specific gravity of the gas component
        :param gas_oil_ratio: The ratio of gas to oil in the mixture

        :return: The density of the mixture (unit = lb/ft**3)
        """
        solution_gor = self.solution_gas_oil_ratio(stream,
                                                   oil_specific_gravity,
                                                   gas_specific_gravity,
                                                   gas_oil_ratio)
        volume_factor = self.formation_volume_factor(stream,
                                                     oil_specific_gravity,
                                                     gas_specific_gravity,
                                                     gas_oil_ratio)

        water_density = self.water.density_STP
        air_density = self.dry_air.density()
        result =\
            (water_density * oil_specific_gravity + air_density * gas_specific_gravity * solution_gor) / volume_factor
        return result.to("lb/ft**3")

    def volume_flow_rate(self, stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio):
        """
        Calculate the oil volume flow rate

        :param stream:
        :param oil_specific_gravity:
        :param gas_specific_gravity:
        :param gas_oil_ratio:

        :return:(float) oil volume flow rate (unit = bbl/day)
        """

        mass_flow_rate = stream.liquid_flow_rate("oil")
        density = self.density(stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio)

        volume_flow_rate = (mass_flow_rate / density).to("bbl_oil/day")
        return volume_flow_rate

    def mass_energy_density(self, API=None, use_LHV=True, with_unit=True):
        """
        Calculate oil heating value

        :param API:
        :param use_LHV: whether to use LHV or HHV
        :param with_unit: (float) lower or higher heating value (unit = btu/lb)

        :return: heating value mass
        """
        # Oil lower heating value correlation
        a1, a2, a3, a4 = (16796, 54.4, 0.217, 0.0019) if use_LHV else (17672, 66.6, 0.316, 0.0014)
        API = self.API.m if API is None else API.m

        result = (a1 + a2 * API - a3 * API ** 2 - a4 * API ** 3)
        result = ureg.Quantity(result, "british_thermal_unit/lb") if with_unit else result

        return result

    def volume_energy_density(self, stream, oil_specific_gravity, gas_specific_gravity, gas_oil_ratio):
        """
        Calculate oil volume energy density

        :param stream:
        :param oil_specific_gravity:
        :param gas_specific_gravity:
        :param gas_oil_ratio:

        :return:(float) volume energy density (unit = mmBtu/bbl)
        """
        mass_energy_density = self.mass_energy_density(API=stream.API)
        density = self.density(stream,
                               oil_specific_gravity,
                               gas_specific_gravity,
                               gas_oil_ratio).to("lb/bbl_oil")

        result = mass_energy_density * density
        return result.to("mmBtu/bbl_oil")

    def energy_flow_rate(self, stream):
        """
        Calculate the energy flow rate in "mmbtu/day" in LHV.

        :stream: (opgee.Stream) the `Stream` to consider

        :return:(pint.Quantity) energy flow rate in "mmBtu/day"
        """
        mass_flow_rate = stream.liquid_flow_rate("oil") + stream.liquid_flow_rate("PC")
        mass_energy_density = self.mass_energy_density(API=stream.API)
        result = (mass_energy_density * mass_flow_rate).to("mmbtu/day")
        return result

    @staticmethod
    def specific_heat(API, temperature):
        """
        Campbell specific heat capacity of oil
        Campbell equation from Manning and Thompson (1991). cp = (-1.39e-6 * T + 1.847e-3)*API+6.32e-4*T+0.352

        :param API:
        :param temperature:

        :return:(float) specific heat capacity of crude oil (unit = btu/lb/degF)
        """
        a1 = -1.39e-6
        a2 = 1.847e-3
        a3 = 6.32e-4
        a4 = 3.52e-1

        API = API.m
        temperature = temperature.to("degF")
        temperature = temperature.m

        heat_capacity = (a1 * temperature + a2) * API + a3 * temperature + a4
        return ureg.Quantity(heat_capacity, "btu/lb/degF")

    # Combustion properties as a fuel

    @staticmethod
    def liquid_fuel_composition(API):
        """
        calculate Carbon, Hydrogen, Sulfur, Nitrogen mol per crude oil
        reference: Fuel Specs, Table Crude oil chemical composition

        :return:(float) liquid fuel composition (unit = mol/kg)
        """
        low_bound = 4
        high_bound = 50

        if API.m < low_bound or API.m > high_bound:
            raise ModelValidationError(f"{API.m} is less than {low_bound} or greater than {high_bound}")

        nitrogen_weight_percent = ureg.Quantity(0.2, "percent")
        sulfur_weight_percent = ureg.Quantity(-0.121 * API.m + 5.4293, "percent")
        hydrogen_weight_percent = ureg.Quantity(0.111 * API.m + 8.7523, "percent")
        carbon_weight_percent = (ureg.Quantity(100., "percent") -
                                 nitrogen_weight_percent -
                                 sulfur_weight_percent -
                                 hydrogen_weight_percent)
        nitrogen_mol_percent = nitrogen_weight_percent / ureg.Quantity(14., "g/mol")
        sulfur_mol_percent = sulfur_weight_percent / ureg.Quantity(32., "g/mol")
        hydrogen_mol_percent = hydrogen_weight_percent / ureg.Quantity(1., "g/mol")
        carbon_mol_percent = carbon_weight_percent / ureg.Quantity(12., "g/mol")

        return pd.Series([carbon_mol_percent, sulfur_mol_percent, hydrogen_mol_percent, nitrogen_mol_percent],
                         index=["C", "S", "H", "N"], dtype="pint[mol/kg]")


class Gas(AbstractSubstance):
    """
    Describes the thermodynamic properties of gas.
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

    def molar_flow_rate(self, stream, name):
        """
        get molar flow rate from stream

        :param stream:
        :param name:

        :return: (float) molar flow rate (unit = mol/day)
        """

        mass_flow_rate = stream.gas_flow_rate(name)
        molar_flow_rate = (mass_flow_rate / self.component_MW[name]).to("mol/day")

        return molar_flow_rate

    def molar_flow_rates(self, stream):
        """
        get molar flow rate from stream

        :param stream:
        :param name:

        :return: (float) molar flow rate (unit = mol/day)
        """

        return pd.Series({name: self.molar_flow_rate(stream, name) for name in stream.component_names})

    def component_molar_fraction(self, name, stream):
        """

        :param name: (str) component name
        :param stream:

        :return:
        """
        total_molar_flow_rate = self.total_molar_flow_rate(stream)
        mass_flow_rate = stream.gas_flow_rate(name)
        molecular_weight = ChemicalInfo.mol_weight(name)
        molar_flow_rate = mass_flow_rate.to("g/day") / molecular_weight

        result = molar_flow_rate / total_molar_flow_rate
        return result.to("frac")

    def component_molar_fractions(self, stream, index=None):
        """

        :param stream:
        :param index: Gas Component's Index Array

        :return:(float) Panda Series component molar fractions
        """

        total_molar_flow_rate = self.total_molar_flow_rate(stream)
        gas_flow_rates = stream.gas_flow_rates(index)

        if len(gas_flow_rates) == 0:
            raise ModelValidationError("Can't compute molar fractions on an empty stream")

        if index is not None:
            molar_flow_rate = gas_flow_rates / self.component_MW[index]
        else:
            molar_flow_rate = gas_flow_rates / self.component_MW[gas_flow_rates.index]

        result = molar_flow_rate / total_molar_flow_rate
        result = pd.Series(result, dtype="pint[fraction]")  # convert units
        return result

    def component_mass_fractions(self, molar_fracs):
        """
        generate mass fractions from molar fractions

        :param molar_fracs:

        :return:
        """
        molar_weight = self.molar_weight_from_molar_fracs(molar_fracs)
        mass_frac = molar_fracs * self.component_MW[molar_fracs.index] / molar_weight

        return mass_frac

    def specific_gravity(self, stream):
        """

        :param stream:

        :return:
        """
        mol_fracs = self.component_molar_fractions(stream)
        sg = (mol_fracs * self.component_MW[mol_fracs.index]).sum()
        sg = sg / self.dry_air.mol_weight
        return sg

    def ratio_of_specific_heat(self, stream):
        """

        :param stream:

        :return:
        """
        mass_flow_rate = stream.gas_flow_rates()  # pandas.Series
        universal_gas_constants = self.model.const("universal-gas-constants")  # J/mol/K
        molecular_weight = self.component_MW[mass_flow_rate.index]
        Cp = self.component_Cp_STP[mass_flow_rate.index]
        gas_constant = universal_gas_constants / molecular_weight
        Cv = Cp - gas_constant
        specific_heat_press = (mass_flow_rate * Cp).sum()
        specific_heat_volm = (mass_flow_rate * Cv).sum()

        ratio_of_specific_heat = specific_heat_press / specific_heat_volm
        return ratio_of_specific_heat.to("frac")

    @staticmethod
    def heat_capacity(stream):
        """

        :param stream:

        :return: (float) gas heat capacity (unit = btu/degF/day)
        """
        temperature = stream.tp.T
        temperature = temperature.to("kelvin").m
        mass_flow_rate = stream.gas_flow_rates()  # pandas.Series
        if mass_flow_rate.empty:
            return ureg.Quantity(0., "btu/degF/day")

        specific_heat = pd.Series({name: Cp(name, temperature, with_units=False) for name in mass_flow_rate.index},
                                  dtype="pint[joule/g/kelvin]")
        heat_capacity = (mass_flow_rate * specific_heat).sum()

        return heat_capacity.to("btu/degF/day")

    def uncorrected_pseudocritical_temperature_and_pressure(self, stream):
        """
        Calculate the uncorrected pseudocritical temperature and pressure for a given stream.

        :param stream: Stream object with gas composition and flow rates
        :return: pandas.Series containing temperature (in Rankine) and pressure (in psia)
        """
        mass_flow_rate = stream.gas_flow_rates()  # pandas.Series
        molar_fraction = self.component_molar_fractions(stream).pint.m
        critical_temperature = self.component_Tc[mass_flow_rate.index].pint.to("rankine")
        critical_temperature = critical_temperature.pint.m
        critical_pressure = self.component_Pc[mass_flow_rate.index].pint.to("psia")
        critical_pressure = critical_pressure.pint.m
        temp1 = (molar_fraction * critical_temperature / critical_pressure ** 0.5).sum()
        temp2 = (molar_fraction * critical_temperature / critical_pressure).sum()
        temp3 = (molar_fraction * (critical_temperature / critical_pressure) ** 0.5).sum()

        temp1 = temp1 ** 2
        temp2 = 1 / 3 * temp2
        temp3 = 2 / 3 * temp3 ** 2
        temperature = ureg.Quantity(temp1 / (temp2 + temp3), "rankine")
        pressure = ureg.Quantity(temp1 / (temp2 + temp3) ** 2, "psia")
        return pd.Series(data=[temperature, pressure], index=["temperature", "pressure"])

    def corrected_pseudocritical_temperature(self, stream):
        """
        Calculate the corrected pseudocritical temperature for a given stream.

        :param stream: Stream object with gas composition and flow rates
        :return: float representing the corrected pseudocritical temperature (in Rankine)
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
        Calculate the corrected pseudocritical pressure for a given stream.

        :param stream: Stream object with gas composition and flow rates
        :return: float representing the corrected pseudocritical pressure (in psia)
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
        result = stream.tp.T.to("rankine") / corr_pseudocritical_temp

        return result.to("frac")

    def reduced_pressure(self, stream):
        """

        :param stream:

        :return:
        """
        corr_pseudocritical_press = self.corrected_pseudocritical_pressure(stream)
        result = stream.tp.P / corr_pseudocritical_press

        return result.to("frac")

    @staticmethod
    def Z_factor(reduced_temperature, reduced_pressure):
        """
        Calculate the compressibility factor (Z) for a given reduced temperature and reduced pressure
        using the Redlich-Kwong equation of state. The Redlich-Kwong equation of state is a cubic equation.
        The function calculates the three possible roots (real or complex) and returns the highest real root as
        the compressibility factor. The input quantities are first converted to dimensionless fractions.

        Args:
            reduced_temperature (pint.Quantity): Reduced temperature as a Pint Quantity object, defined as T/Tc (ratio of temperature to critical temperature).
            reduced_pressure (pint.Quantity): Reduced pressure as a Pint Quantity object, defined as P/Pc (ratio of pressure to critical pressure).

        Returns:
            pint.Quantity: Compressibility factor (Z) as a Pint Quantity object (dimensionless fraction) for the given reduced temperature and reduced pressure.

        """
        tr = reduced_temperature.to("frac").m
        pr = reduced_pressure.to("frac").m

        a = 0.42748 * (pr / tr ** 2.5)
        b = 0.08664 * (pr / tr)

        alpha = (1 / 3) * (3 * (a - b - b ** 2) - 1)
        beta = (1 / 27) * (-2 + (9 * (a - b - b ** 2)) - (27 * a * b))
        d = (beta ** 2 / 4) + (alpha ** 3 / 27)

        if d < 0:
            theta = math.acos(-np.sign(beta) * (math.sqrt((beta ** 2 / 4) / (-alpha ** 3 / 27))))
            z_roots = [2 * math.sqrt(- alpha / 3) * math.cos((theta / 3) + (i * ((math.pi * 2) / 3))) + (1 / 3) for i in
                       range(3)]
        else:
            a_star = np.cbrt((-beta / 2) + np.sqrt(d))
            b_star = np.cbrt((-beta / 2) - np.sqrt(d))
            z_roots = [a_star + b_star + 1 / 3] if d > 0 else [a_star + b_star + 1 / 3] + [
                -(1 / 2) * (a_star + b_star) + (1 / 3) * i for i in [2, 3]]

        z = max(z_roots)

        return ureg.Quantity(z, "frac")

    def volume_factor(self, stream):
        """

        :param stream:

        :return:
        """

        z_factor = self.Z_factor(self.reduced_temperature(stream), self.reduced_pressure(stream))
        stream_T = stream.tp.T.to("rankine")
        stream_P = stream.tp.P
        amb_temp = STP.T.to("rankine")
        amb_press = STP.P

        result = amb_press * z_factor * stream_T / (stream_P * amb_temp)
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
        temp = stream.tp.T.to("rankine").m

        factor_K = (9.4 + 0.02 * gas_stream_molar_weight) * temp ** 1.5 / (209 + 19 * gas_stream_molar_weight + temp)
        factor_X = 3.5 + 986 / temp + 0.01 * gas_stream_molar_weight
        factor_Y = 2.4 - 0.2 * factor_X

        viscosity = 1.10e-4 * factor_K * math.exp(factor_X * (gas_density / 62.4) ** factor_Y)
        return ureg.Quantity(viscosity, "centipoise")

    def molar_weight_from_molar_fracs(self, molar_fracs):
        """
        Calculate molar weight from molar fraction, where molar fraction is stored in Pandas Series

        :param molar_fracs:

        :return: (float) molar weight (unit = g/mol)
        """
        molar_weight = (self.component_MW[molar_fracs.index] * molar_fracs).sum()

        return molar_weight.to("g/mol")

    def molar_weight(self, stream):
        """

        :param stream:

        :return:
        """
        mol_fracs = self.component_molar_fractions(stream)
        return self.molar_weight_from_molar_fracs(mol_fracs)

    def volume_flow_rate(self, stream):
        """
        Calculate volume flow rate from given stream.

        :param stream:

        :return: (Float) Total gas volume flow rate, unit = m3/day
        """
        total_mass_rate = stream.total_gas_rate()
        density = self.density(stream)

        volume_flow_rate = total_mass_rate / density
        return volume_flow_rate

    def volume_flow_rate_STP(self, stream):
        """
        Calculate volume flow rate from given stream under standard condition

        :param stream:
        :return: (Float) Total gas volume flow rate, unit = m3/day
        """
        return self.volume_flow_rates_STP(stream).sum()

    def volume_flow_rates_STP(self, stream):
        """
        Calculate volume flow rates from given stream under standard condition

        :param stream:
        :return: (pd.Series) gas volume flow rates, unit = m3/day
        """
        stream_STP = Stream("stream_STP", tp=STP)
        stream_STP.copy_flow_rates_from(stream, tp=STP)

        result = stream_STP.gas_flow_rates() / self.component_gas_rho_STP[stream_STP.gas_flow_rates().index]
        return result

    def mass_energy_density(self, stream):
        """

        :param stream: (opgee.Stream) the `Stream` to examine
        :return: (float) gas mass energy density (unit = MJ/kg); None if the stream is empty
        """
        mass_flow_rate = stream.gas_flow_rates()

        if len(mass_flow_rate) == 0:
            return ureg.Quantity(0., "MJ/kg")

        total_mass_rate = stream.total_gas_rate()

        hv_molar = self.component_LHV_molar
        hv = hv_molar[mass_flow_rate.index]

        molecular_weight = self.component_MW[mass_flow_rate.index]
        mass_energy_density = (mass_flow_rate / total_mass_rate * hv / molecular_weight).sum()

        return mass_energy_density.to("MJ/kg")

    def mass_energy_density_from_molar_fracs(self, molar_fracs):
        """
        calculate gas mass energy density from series

        :param molar_fracs:
        :return: (float) gas mass energy density (unit = MJ/kg)
        """
        hv_molar = self.component_LHV_molar

        hv = hv_molar[molar_fracs.index]
        molecular_weight = self.component_MW[molar_fracs.index]
        mass_energy_density = (hv * molar_fracs / molecular_weight).sum()

        return mass_energy_density.to("MJ/kg")

    @staticmethod
    def combustion_enthalpy(molar_fracs, temperature, phase):
        """
        calculate OTSG/HRSG combustion enthalpy

        :param molar_fracs:
        :param temperature:

        :return:
        """

        enthalpy = pd.Series(
            {name: Enthalpy(name, temperature, phase=phase, with_units=False) for name in molar_fracs.index},
            dtype="pint[joule/mole]")

        if "H2O" in molar_fracs and phase == PHASE_GAS:
            steam_table = XSteam(XSteam.UNIT_SYSTEM_FLS)
            temp = temperature.m
            water_vapor_enthalpy = ureg.Quantity(steam_table.hV_t(temp), "btu/lb") * ChemicalInfo.mol_weights()["H2O"]

            water_T_ref = ureg.Quantity(30, "degC")
            water_T_ref = water_T_ref.to("degF").m
            latent_heat_water = \
                ureg.Quantity(
                    steam_table.hV_t(water_T_ref) - steam_table.hL_t(water_T_ref), "btu/lb") * ChemicalInfo.mol_weights()["H2O"]
            enthalpy["H2O"] = max(water_vapor_enthalpy - latent_heat_water, ureg.Quantity(0.0, "joule/mole"))

        return enthalpy

    def volume_energy_density(self, stream):
        """
        Calculate gas volume energy density

        :param stream:

        :return:(float) gas volume energy density (unit = btu/scf)
        """
        mass_flow_rate = stream.gas_flow_rates()  # pandas.Series

        lhv = self.component_LHV_molar[mass_flow_rate.index]
        molecular_weight = self.component_MW[mass_flow_rate.index]
        density = self.component_gas_rho_STP[mass_flow_rate.index]
        molar_fraction = self.component_molar_fractions(stream)
        volume_energy_density = (molar_fraction * density * lhv / molecular_weight).sum()

        return volume_energy_density.to("Btu/ft**3")

    def energy_flow_rate(self, stream):
        """
        Calculate the energy flow rate in "mmbtu/day" in LHV.

        :stream: (opgee.Stream) the `Stream` to consider

        :return:(pint.Quantity) energy flow rate in "mmBtu/day"
        """
        total_mass_flow_rate = stream.total_gas_rate()
        mass_energy_density = self.mass_energy_density(stream)
        result = (total_mass_flow_rate * mass_energy_density).to("mmBtu/day")

        return result


class Water(AbstractSubstance):
    """
    Water class includes the method to calculate water density, water volume flow rate, etc.
    """

    # Required for the lookup steam table, which has a max of 2 digits.
    steam_tbl_digits = 2

    def __init__(self, field):
        super().__init__(field)
        self.TDS = field.attr("total_dissolved_solids")  # mg/L
        # TODO: this can be improved by adding ions in the H2O in the solution
        self.specific_gravity = ureg.Quantity(1 + self.TDS.m * 0.695 * 1e-6, "frac")
        self.density_STP = self.density()

    def density(self, temperature=None, pressure=None):
        """
        water density

        :return: (float) water density (unit = kg/m3)
        """

        temp = temperature if temperature is not None else self.model.const("std-temperature")
        press = pressure if pressure is not None else self.model.const("std-pressure")

        temp = temp.to("degF").m
        press = press.to("psia").m

        specifc_gravity = self.specific_gravity
        water_density = self.steam_table.rho_pt(round(press, self.steam_tbl_digits), round(temp, self.steam_tbl_digits))
        water_density = ureg.Quantity(water_density, "lb/ft**3")
        density = specifc_gravity * water_density

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

    @staticmethod
    def specific_heat(temperature):
        """

        :param temperature:

        :return:(float) water specific heat (unit = btu/lb/degF)
        """
        temperature = temperature.to("kelvin").m
        specific_heat = Cp("H2O", temperature)
        return specific_heat.to("btu/lb/degF")

    @classmethod
    def heat_capacity(cls, stream):
        """

        :param stream:

        :return: (float) water heat capacity (unit = btu/degF/day)
        """
        mass_flow_rate = stream.liquid_flow_rate("H2O")
        specific_heat = cls.specific_heat(stream.tp.T)

        heat_capacity = mass_flow_rate * specific_heat
        return heat_capacity.to("btu/degF/day")

    @staticmethod
    def saturated_temperature(saturated_pressure):
        """
        calculate water saturated temperature given the saturated pressure

        :param saturated_pressure:

        :return: (float) water saturated temperature (unit = degF)
        """

        psat = saturated_pressure.to("Pa").m
        saturated_temp = Tsat("H2O", psat, with_units=True)

        return saturated_temp

    def enthalpy_PT(self, pressure, temperature, mass_rate):
        """
        calculate water enthalpy given pressure and temperature

        :param pressure:
        :param temperature:
        :param mass_rate:

        :return: (float) total water enthalpy (unit = MJ/day)
        """
        pressure = pressure.to("psia").m
        temperature = temperature.to("degF").m

        enthalpy = self.steam_table.h_pt(round(pressure, self.steam_tbl_digits),
                                         round(temperature, self.steam_tbl_digits))
        enthalpy = ureg.Quantity(enthalpy, "btu/lb")

        result = enthalpy * mass_rate
        return result.to("MJ/day")

    def steam_enthalpy(self, pressure, steam_quality, mass_rate):
        """
        calculate steam enthalpy from steam quality

        :param pressure:
        :param steam_quality:
        :param mass_rate:

        :return:
        """
        pressure = pressure.to("psia").m
        vapor_enthalpy = self.steam_table.hV_p(round(pressure, self.steam_tbl_digits))
        vapor_enthalpy = ureg.Quantity(vapor_enthalpy, "btu/lb")
        liquid_enthalpy = self.steam_table.hL_p(round(pressure, self.steam_tbl_digits))
        liquid_enthalpy = ureg.Quantity(liquid_enthalpy, "btu/lb")

        result = vapor_enthalpy * steam_quality + liquid_enthalpy * (1 - steam_quality)
        result = mass_rate * result
        return result.to("MJ/day")
