from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)


class CrudeOilStorage(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        if field.attr("crude_oil_dewatering_output") != self.name:
            self.enabled = False
            return
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        input_stab_oil = self.find_input_stream("oil for stabilization")


        # solution_GOR = oil.solution_gas_oil_ratio(stream,
        #                                                 oil.oil_specific_gravity,
        #                                                 oil.gas_specific_gravity,
        #                                                 oil.gas_oil_ratio)