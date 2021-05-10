from ..core import OpgeeObject
import numpy as np
from ..opgee_tools_wl.constant import moles_of_gas_per_SCF_STP
from thermosteam import Chemical, Mixture
from ..stream import PHASE_GAS, PHASE_SOLID, PHASE_LIQUID

gases = ["N2", "O2", "CO2", "H2O", "CH4", "CO2", "H2", "H2S", "SO2", "C2H6", "C3H8", "C4H10"]
dict_gas  = {name: Chemical(name) for name in gases}

class WetAir(OpgeeObject):
    def __init__(self):
        self.components = ["N2", "O2", "CO2", "H2O"]
        self.mol_fraction = [0.774396, 0.20531, 0.000294, 0.02]
        self.mixture = Mixture.from_chemicals(self.components)

    def MW(self):
        return self.mixture.MW(self.mol_fraction)

class Hydrocarbon(OpgeeObject):
    def __init__(self, res_temp, res_press):
        self.res_temp = res_temp
        self.res_press = res_press

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
        self.wet_air_MW = WetAir().MW

    def gas_specific_gravity(self):
        """
        Gas specific gravity is defined as the ratio of the molecular weight (MW) of the gas
        to the MW of wet air

        :return: (float) gas specific gravity (unit = fraction)
        """
        gas_comp = self.gas_comp
        gas_SG = 0
        for name, value in gas_comp.items():
            if value > 0:
                # TODO: name = carbon_number_to_molecule(name)
                mw = dict_gas[name].MW
                # TODO: take to Rich, this is not a unit conversion, because the scf is always = 1
                density = moles_of_gas_per_SCF_STP * mw
                gas_SG += density * value
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
        res_temperature = self.res_temp
        res_pressure = self.res_press
        gas_SG = self.gas_specific_gravity()
        gor_bubble = self.bubble_point_solution_GOR()

        result = np.min([
            res_pressure ** (1 / pbub_a2) *
            oil_SG ** (-pbub_a1 / pbub_a2) *
            np.exp(pbub_a3 / pbub_a2 * gas_sg * oil_sg) /
            (res_temperature.to("rankine") * gas_SG) ,
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
        res_temperature = self.res_temp

        gas_SG = self.gas_specific_gravity()
        gor_bubble = self.bubble_point_solution_GOR()

        result = (oil_SG ** pbub_a1 *
                  (gas_SG * gor_bubble * res_temperature.to("rankine")) ** pbub_a2 *
                  np.exp(-pbub_a3 * gas_SG * oil_SG))
        return result

    def bubble_point_formation_volume_factor(self):
        """
        the formation volume factor is defined as the ratio of the volume of oil (plus the gas in solution)
        at the prevailing reservoir temperature and pressure to the volume of oil at standard conditions

        :return: (float) bubblepoint formation volume factor (unit = fraction)
        """
        oil_SG = self.oil_specific_gravity
        res_temperature = self.res_temp

        gas_SG = self.gas_specific_gravity()
        res_GOR = self.reservoir_solution_GOR()

        result = (oil_FVF_bub_a1 + oil_FVF_bub_a2 * res_GOR * (res_temperature - 60) +
                  oil_FVF_bub_a3 * res_GOR / oil_SG + oil_FVF_bub_a4 * (res_temperature - 60) /
                  oil_SG + O_FVF_bub_a5 * res_GOR * gas_SG / oil_SG)
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

        gas_SG = self.gas_specific_gravity()
        gor_bubble = self.bubble_point_solution_GOR()

        result = np.min[np.power(stream.pressure, 1 / pbub_a2) *
                        np.power(oil_SG, -pbub_a1 / pbub_a2) *
                        np.exp(pbub_a3 / pbub_a2 * gas_SG * oil_SG) *
                        1 / (stream.temperature.to("rankine") * gas_SG),
                        gor_bubble]
        return result
        #TODO:
        # 3. ask Adam to get the formula reference
        # temp1 = np.power(stream.pressure, 1 / pbub_a2)
        # temp2 = np.power(oil_SG, -pbub_a1 / pbub_a2)
        # temp3 = np.exp(pbub_a3 / pbub_a2 * gas_SG * oil_SG)
        # TODO: unit coversion, ask Rich if this in the correct conversion
        # temp4 = 1 / (stream.temperature.to("rankine") * gas_SG)
        # return np.min([temp1 * temp2 * temp3 * temp4, gor_bubble])

    def _saturated_formation_volume_factor(self):
        """
        the formation volume factor is defined as the ratio of the volume of oil (plus the gas in solution)
        at the prevailing reservoir temperature and pressure to the volume of oil at standard conditions

        :return: (float) saturated formation volume factor (unit = fraction)
        """
        API = self.API
        gas_comp = self.gas_comp
        oil_SG = self.oil_specific_gravity

        gas_SG = self.gas_specific_gravity()
        solution_gor = self.solution_gas_oil_ratio()

        result = (1 + 0.000000525 * solution_gor * (temperature - 60) +
                  0.000181 * solution_gor / oil_SG + 0.000449 * (temperature - 60) / oil_SG +
                  0.000206 * solution_gor * gas_SG / oil_SG)
        return result

    def _unsat_formation_volume_factor(self):
        """
        the formation volume factor is defined as the ratio of the volume of oil (plus the gas in solution)
        at the prevailing reservoir temperature and pressure to the volume of oil at standard conditions

        :return: (float) unsaturated formation volume factor (unit = fraction)
        """
        bubble_oil_FVF = self.bubble_point_formation_volume_factor()
        p_bubblepoint = self.bubble_point_pressure()

        result = bubble_oil_FVF * np.exp(self.isothermal_compressibility() * (p_bubblepoint - pressure))
        return result

    def isothermal_compressibility_X(self, stream):
        """
        Isothermal compressibility is the change in volume of a system as the pressure changes while temperature remains constant.

        :return:
        """
        solution_gor = self.solution_gas_oil_ratio()
        gas_SG = self.gas_specific_gravity()

        result = (iso_comp_a1 * solution_gor + iso_comp_a2 * solution_gor ** 2 +
                  iso_comp_a3 * gas_SG + iso_comp_a4 * stream.temperature.to("rankine") ** 2)
        return result

    def isothermal_compressibility(self):
        """
        Regression from ...

        :return:
        """
        oil_SG = self.oil_specific_gravity()
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
            result = self._saturated_formation_volume_factor()
        else:
            result = self._unsat_formation_volume_factor()
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
        #TODO: ask Rich if this is the right way to get the phase mass rate
        mass_flow_rate = stream.hydrocarbon_rate(PHASE_LIQUID)
        mass_energy_density = self.mass_energy_density()

        #TODO: ask Rich, what is the best way to direct convert tonne/day to lb/day
        result = mass_energy_density * mass_flow_rate.to("lb/day")
        return result


class Gas(Hydrocarbon):
    def __init__(self, res_temp, res_press):
        super().__init__(res_temp, res_press)

