from ..core import Process
from ..log import getLogger

_logger = getLogger(__name__)

class ReservoirWellInterface(Process):
    def __init__(self, name, attr_dict=None):
        inputs  = [1, 100, 25, 91]
        outputs = [3, 101, 26]

        super().__init__(name, inputs=inputs, outputs=outputs, attr_dict=attr_dict)


    def run(self, level, **kwargs):
        self.print_running_msg(level)
