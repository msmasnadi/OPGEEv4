from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__) # data logging

class ReservoirWellInterface(Process):
    def run(self, analysis):
        _logger.debug("test message")
        self.print_running_msg()

        field = self.get_field()

        # collect the "gas_comp_*" attributes in a pandas.Series
        gas_comp = field.attrs_with_prefix('gas_comp_')
        # oil_comp =

        N2  = gas_comp.N2
        CO2 = gas_comp.CO2

        # examples of getting attribute values
        num_wells = field.attr('num_prod_wells')
        depth = field.attr('depth')
        GOR = field.attr('GOR')
        _logger.info(f"{self.name}: wells:{num_wells} depth:{depth} GOR:{GOR}")

        # Functions to set energy use and emission rates
        # self.add_energy_rate(carrier, rate)
        # self.add_energy_rates(dictionary=d)
        # self.add_emission_rate('CO2', rate)
        # self.add_emission_rates(CO2=rate1, N2O=rate2, ...)

    def impute(self):
        # TBD: copy from output streams to input streams
        pass
