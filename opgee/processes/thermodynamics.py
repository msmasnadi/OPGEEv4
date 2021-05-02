from ..core import OpgeeObject
import numpy as np
import constant as const
import pyromat as py
import thermosteam as tmo

gases = ["N2", "O2", "CO2", "H2O", "CH4", "CO2", "H2", "H2S", "SO2"]
pyromat_gases = ["C2H6", "C3H8", "C4H10", "air"] + gases
thermo_gases = ["Ethane", "Propane", "Butane"] + gases
dict_gas_pyromat = {name:py.get("ig." + name) for name in pyromat_gases}
dict_gas_thermo = {name:py.get("ig." + name) for name in thermo_gases}

class Oil(OpgeeObject):
    # Bubblepoint pressure constants
    pbub_a1 = 5.527215
    pbub_a2 = 0.783716
    pbub_a3 = 1.841408

    def __init__(self, API, gas_comp, gas_oil_ratio):
        """

        :param API:
        :param gas_comp:
        :param gas_oil_ratio:
        """
        self.API = API
        self.gas_comp = gas_comp
        self.gas_oil_ratio = gas_oil_ratio

        # self.x = None
        pass

    def gas_specific_gravity(self):
        gas_comp = self.gas_comp
        gas_SG = 0
        for name, value in gas_comp.items():
            if value > 0:
                mw = dict_gas_pyromat[name].mw()
                density = const.moles_of_gas_per_SCF_STP * mw
                gas_SG += density * value
        return gas_SG / dict_gas_pyromat["Air"].mw()

    # TODO: we can treat is as unit conversion
    @staticmethod
    def oil_specific_gravity(self):
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

    def solution_gas_oil_ratio(self):
        # TODO: ask Rich if I need to call the self.varible
        API = self.API
        gas_comp = self.gas_comp
        GOR = self.gas_oil_ratio

        gas_SG = gas_specific_gravity(gas_comp)
        oil_SG = oil_specific_gravity(API)
        GOR_bubble = bubble_point_solution_GOR(GOR)

        #TODO:
        # 1. ask Rich how to deal with long equation
        # 2. where to get stream variable such as temp and pres
        temp1 = np.power(pressure, 1 / pbub_a2)
        temp2 = np.power(gamma_o, -pbub_a1 / pbub_a2)
        temp3 = np.exp(pbub_a3 / pbub_a2 * gas_SG * oil_SG)
        temp4 = 1 / ((460 + temperature) * gas_SG)
        return np.min([temp1 * temp2 * temp3 * temp4, GOR_bubble])
