from ..process import Process
from ..log import getLogger
from ..stream import Stream

_logger = getLogger(__name__)


class CrudeOilStorage(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        oil_mass_rate = 0
        input_stab_oil = self.find_input_stream("oil for stabilization", raiseError=False)
        if input_stab_oil is not None:
            oil_mass_rate += input_stab_oil.liquid_flow_rate("oil")

        input_updated_oil = self.find_input_stream("oil for upgrader", raiseError=False)
        if input_updated_oil is not None:
            oil_mass_rate += input_updated_oil.liquid_flow_rate("oil")

        input_diluted_oil = self.find_input_stream("oil for dilution", raiseError=False)
        if input_diluted_oil is not None:
            oil_mass_rate += input_diluted_oil.liquid_flow_rate("oil")

        # TODO: get solution GOR inlet from separation
        stream = Stream(temperature=self.std_temp, pressure=self.std_press)
        oil = self.field.Oil
        solution_GOR_outlet = oil.solution_gas_oil_ratio(stream,
                                                         oil.oil_specific_gravity,
                                                         oil.gas_specific_gravity,
                                                         oil.gas_oil_ratio)

