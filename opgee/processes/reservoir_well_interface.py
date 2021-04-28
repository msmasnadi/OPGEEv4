from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__) # data logging

class ReservoirWellInterface(Process):
    def run(self, **kwargs):
        _logger.debug("test message")
        self.print_running_msg()

        field = self.get_field()

        # collect the "gas_comp_*" attributes in a pandas.Series
        gas_comp = field.attrs_with_prefix('gas_comp_')

        N2  = gas_comp.N2
        CO2 = gas_comp.CO2

        # examples of getting attribute values
        num_wells = field.attr('num_prod_wells')
        depth = field.attr('depth')
        GOR = field.attr('GOR')
        _logger.info(f"{self.name}: wells:{num_wells} depth:{depth} GOR:{GOR}")


    def impute(self):
        # TBD: copy from output streams to input streams
        pass
