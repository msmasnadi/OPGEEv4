from ..core import OpgeeObject
import numpy as np
from ..opgee_tools_wl import constant as const      # TODO: remove this after constants are migrated
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

    def __init__(self, API, gas_comp, gas_oil_ratio):
        """

        :param API:
        :param gas_comp:
        :param gas_oil_ratio:
        """
        self.API = API
        self.gas_comp = gas_comp
        self.gas_oil_ratio = gas_oil_ratio

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
        Since OPGEE takes separator gas oil ratio as an input, we use this.

        :return:(float) GOR at bubblepoint
        """
        # Wennan, note that the auto-documentation system requires a blank line between the description and the list
        # of variables / return values, as I've done above.

        #TODO: ask Rich if the unit comment is needed
        # Answer: we'll eventually use pint here, so the result will have the same units as the input, right?
        # If not, we'll define 1.1618 as a factor in a unit conversion in units.txt. I'm not sure which is correct.

        # gor = self.gas_oil_ratio # There's no benefit to assigning this to a local variable to use it just once.

        return self.gas_oil_ratio * 1.1618

    def solution_gas_oil_ratio(self, stream):
        # TODO: ask Rich if I need to call the self.variable
        API = self.API
        gas_comp = self.gas_comp
        GOR = self.gas_oil_ratio

        gas_SG = self.gas_specific_gravity(gas_comp)
        oil_SG = self.oil_specific_gravity(API)
        GOR_bubble = self.bubble_point_solution_GOR(GOR)

        #TODO:
        # 1. ask Rich how to deal with long equation
        #    - Answer: what you've done seems fine. Breaking it into chunks like
        #      this makes it easy to run in the debugger and verify each step, at
        #      no real cost to performance. Plus it's more readable.
        # 2. where to get stream variable such as temp and pres
        #    - Answer: pass the stream from the Process


        temp1 = np.power(stream.pressure, 1 / self.pbub_a2)

        # TODO: Wennan, isn't 'gamma_o' now replaced with oil_SG?
        # temp2 = np.power(gamma_o, -self.pbub_a1 / self.pbub_a2)
        temp2 = np.power(oil_SG, -self.pbub_a1 / self.pbub_a2)

        temp3 = np.exp(self.pbub_a3 / self.pbub_a2 * gas_SG * oil_SG)
        temp4 = 1 / ((460 + stream.temperature) * gas_SG)
        return np.min([temp1 * temp2 * temp3 * temp4, GOR_bubble])
