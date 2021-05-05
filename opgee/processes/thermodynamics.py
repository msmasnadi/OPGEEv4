from ..core import OpgeeObject
import numpy as np
from ..opgee_tools_wl.constant import moles_of_gas_per_SCF_STP
import pyromat
from thermosteam import Chemical

gases = ["N2", "O2", "CO2", "H2O", "CH4", "CO2", "H2", "H2S", "SO2"]
pyromat_gases = gases + ["C2H6", "C3H8", "C4H10", "air"]
thermo_gases  = gases + ["Ethane", "Propane", "Butane"]

dict_gas_pyromat = {name: pyromat.get("ig." + name) for name in pyromat_gases}
dict_gas_thermo  = {name: Chemical(name) for name in thermo_gases}

class Oil(OpgeeObject):
    # Bubblepoint pressure constants
    pbub_a1 = 5.527215
    pbub_a2 = 0.783716
    pbub_a3 = 1.841408

    # Isothermal compressibility constants
    iso_comp_a1 = -0.000013668
    iso_comp_a2 = -0.00000001925682
    iso_comp_a3 = 0.02408026
    iso_comp_a4 = -0.0000000926091

    def __init__(self, API, gas_comp, gas_oil_ratio):
        """

        :param API:
        :param gas_comp: (pandas.Series)
        :param gas_oil_ratio:
        """
        self.API = API
        #TODO: unit conversion
        self.oil_specific_gravity = 141.5 / (131.5 + API.m)
        self.gas_comp = gas_comp
        self.gas_oil_ratio = gas_oil_ratio

        # self.x = None
        pass

    def gas_specific_gravity(self):
        gas_comp = self.gas_comp
        gas_SG = 0
        for name, value in gas_comp.items():
            if value > 0:
                name = carbon_number_to_molecule(name)

                mw = dict_gas_pyromat[name].mw()
                # TODO: we need change this
                density = moles_of_gas_per_SCF_STP * mw
                gas_SG += density * value
        return gas_SG / dict_gas_pyromat["Air"].mw()

    # TODO: we can treat is as unit conversion
    @staticmethod
    def specific_gravity(self):
        API = self.API
        return 141.5 / (131.5 + API)

    def bubble_point_solution_GOR(self):
        """
        R_sb = 1.1618 * R_sp R_Sb is GOR at bubblepoint, R_sp is GOR at separator
        Valco and McCain (2002) give a means to estimate the bubble point gas-oil ratio from the separator gas oil ratio.
        Since OPGEE takes separator gas oil ratio as an input, we use this

        :return:(float) GOR at bubblepoint
        """
        #TODO: ask Rich if the unit comment is needed
        gor = self.gas_oil_ratio
        return gor * 1.1618

    def bubble_point_pressure(self, stream):
        """
        
        :return: 
        """
        API = self.API
        gas_comp = self.gas_comp
        GOR = self.gas_oil_ratio

        gas_SG = self.gas_specific_gravity()
        oil_SG = self.specific_gravity()
        gor_bubble = self.bubble_point_solution_GOR()

        temp1 = oil_SG ** pbub_a1
        #TODO: unit coversion
        temp2 = (gas_SG * gor_bubble * (stream.temperature + 459.67)) ** pbub_a2
        temp3 = np.exp(-pbub_a3 * gas_SG * oil_SG)
        return temp1 * temp2 * temp3

    def solution_gas_oil_ratio(self, stream):
        """

        :return:
        """
        API = self.API
        gas_comp = self.gas_comp
        GOR = self.gas_oil_ratio

        gas_SG = gas_specific_gravity(gas_comp)
        oil_SG = oil_specific_gravity(API)
        gor_bubble = bubble_point_solution_GOR(GOR)

        #TODO:
        # 3. ask Adam to get the formula reference
        temp1 = np.power(stream.pressure, 1 / pbub_a2)
        temp2 = np.power(oil_SG, -pbub_a1 / pbub_a2)
        temp3 = np.exp(pbub_a3 / pbub_a2 * gas_SG * oil_SG)
        # TODO: unit coversion
        temp4 = 1 / ((460 + stream.temperature) * gas_SG)
        return np.min([temp1 * temp2 * temp3 * temp4, gor_bubble])

    def saturated_formation_volume_factor(self):
        """

        :return:
        """
        API = self.API
        gas_comp = self.gas_comp

        gas_SG = gas_specific_gravity(gas_comp)
        oil_SG = oil_specific_gravity(API)
        solution_gor = solution_gas_oil_ratio(self)

        temp1 = 1 + 0.000000525 * solution_gor * (temperature - 60)
        temp2 = 0.000181 * solution_gor / oil_SG + 0.000449 * (temperature - 60) / oil_SG
        temp3 = 0.000206 * solution_gor * gas_SG / oil_SG
        return temp1 + temp2 + temp3

    def unsat_formation_volume_factor(self):
        """

        :return:
        """
        O_FVF_bub = fuel.O_FVF_bub(tempt, pressure, API, gas_comp, GOR)
        p_bubblepoint = bubble_point_pressure(self)

        result = O_FVF_bub * np.exp(ISO_CO(API) * (p_bubblepoint - pressure))
        return result

    def isothermal_compressibility_X(self):
        """

        :return:
        """
        solution_gor = solution_gas_oil_ratio(self)
        gas_SG = gas_specific_gravity(self.gas_comp)
        # TODO: ask Rich how to do unit conversion
        T_abs = temperature + 459.67

        result = (iso_comp_a1 * solution_gor + iso_comp_a2 * solution_gor ** 2 +
                  iso_comp_a3 * gas_SG + iso_comp_a4 * T_abs ** 2)
        return result

    def isothermal_compressibility(self):
        """
        Regression from ...

        :return:
        """
        oil_SG = oil_specific_gravity(self.API)
        # TODO: ask Rich how to do conversion: million, thousand, hundred
        return (55.233 - 60.588 * oil_SG) / 1e6
