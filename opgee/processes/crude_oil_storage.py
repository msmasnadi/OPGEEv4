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
        input_stab_oil = self.find_input_stream("oil for stabilization")
        if input_stab_oil is None:
            pass
        input_updated_oil = self.find_input_stream("oil for upgrader")
        input_diluted_oil = self.find_input_stream("oil for dilution")

        stream = Stream(temperature=self.std_temp, pressure=self.std_press)
        oil = self.field.Oil
        solution_GOR_outlet = oil.solution_gas_oil_ratio(stream,
                                                         oil.oil_specific_gravity,
                                                         oil.gas_specific_gravity,
                                                         oil.gas_oil_ratio)
