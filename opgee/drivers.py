from opgee.core import OpgeeObject
from opgee import ureg


class Drivers(OpgeeObject):

    def __init__(self):
        """
        Primary mover type:
        1 = NG engine,
        2 = Electric motor,
        3 = Diesel engine,
        4 = NG turbine
        """

        self.slope = {1: -0.6035,
                      3: -0.4299,
                      4: -0.1279}

        self.intercept = {1: 7922.4,
                          3: 7235.4,
                          4: 9219.6}

    def get_efficiency(self, prime_mover_type, brake_horsepower):
        """

        :param prime_mover_type:
        :param brake_horsepower:
        :return:
        """
        if prime_mover_type == 2: # electricity
            efficiency = 2967 * brake_horsepower.m**(-0.018) if brake_horsepower != 0.0 else 3038
        else:
            efficiency = self.slope[prime_mover_type] * brake_horsepower.m + self.intercept[prime_mover_type]
        return ureg.Quantity(efficiency, "btu/horsepower/hour")
