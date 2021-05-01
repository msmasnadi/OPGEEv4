from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID

_logger = getLogger(__name__)


class ProducedWaterTreatment(Process):
    def run(self, **kwargs):
        field = self.get_field()
        model = self.model
        water_FVF = model.const("water-FVF")

        # collect the "gas_comp_*" attributes in a pandas.Series
        gas_comp = field.oil.gas_comp
        API = field.oil.API
        gas_oil_ratio = field.oil.gas_oil_ratio
        # oil_comp =

        N2 = gas_comp.N2
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
        self.print_running_msg()