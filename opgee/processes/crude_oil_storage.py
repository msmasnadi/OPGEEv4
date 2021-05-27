from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)


class CrudeOilStorage(Process):
    def run(self, analysis):
        self.print_running_msg()

        # solution_GOR = oil.solution_gas_oil_ratio(stream,
        #                                                 oil.oil_specific_gravity,
        #                                                 oil.gas_specific_gravity,
        #                                                 oil.gas_oil_ratio)