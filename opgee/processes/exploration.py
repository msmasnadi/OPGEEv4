from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)


class Exploration(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas

    def run(self, analysis):
        self.print_running_msg()

        field = self.field
        export_df = field.import_export.export_df


