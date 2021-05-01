from ..core import OpgeeObject
import gas_library as gas_lib
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
                mw = gas_lib.dict_gas_pyromat[name].mw()  # g/mol
                density = const.moles_of_gas_per_SCF_STP * mw
                gas_SG += density * value
        return gas_SG / gas_lib.dict_gas_pyromat["Air"].mw()

    # TODO: we can treat is as unit conversion
    @staticmethod
    def specific_gravity(API):
        """

        :param API: (float) API gravity
        :return: (float) specific gravity
        """
        return 141.5 / (131.5 + API)

    def solution_gas_oil_ratio(self):
        gas_SG = thermo_f.gas_sg(gas_comp)
        GOR_bubble = fuel.GOR_bubblepoint(GOR)
        gamma_o = GAMMA_O(API)

        # see OPGEE v3.0a Flow Sheet tab row 33
        first_part = np.power(pressure, 1 / pbub_a2)
        second_part = np.power(gamma_o, -pbub_a1 / pbub_a2)
        third_part = np.exp(pbub_a3 / pbub_a2 * gas_SG * gamma_o)
        forth_part = 1 / ((460 + tempt) * gas_SG)
        return np.min([first_part * second_part * third_part * forth_part, GOR_bubble])  # scf/bbl
