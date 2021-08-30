from ..process import Process
from ..log import getLogger
from opgee import ureg
from ..stream import Stream
from ..emissions import EM_FLARING

_logger = getLogger(__name__)


class Flaring(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.mol_per_scf = field.model.const("mol-per-scf")
        self.FOR = field.attr("FOR")
        self.oil_volume_rate = field.attr("oil_prod")
        #TODO: need to work on this
        self.combusted_gas_frac = field.attr("combusted_gas_frac")

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        input = self.find_input_streams("gas", combine=True)

        gas_mol_fraction = self.gas.total_molar_flow_rate(input)
        gas_volume_rate = gas_mol_fraction / self.mol_per_scf
        volume_of_gas_flared = self.oil_volume_rate * self.FOR
        frac_gas_flared = min(ureg.Quantity(1, "frac"), volume_of_gas_flared / gas_volume_rate)

        methane_slip = Stream("methane_slip", temperature=input.temperature, pressure=input.pressure)
        methane_slip.copy_flow_rates_from(input)
        multiplier = (frac_gas_flared * (1 - self.combusted_gas_frac)).m
        methane_slip.multiply_flow_rates(multiplier)

        gas_to_flare = Stream("gas_to_flare", temperature=input.temperature, pressure=input.pressure)
        gas_to_flare.copy_flow_rates_from(input)
        gas_to_flare.multiply_flow_rates(frac_gas_flared.m)
        gas_to_flare.subtract_gas_rates_from(methane_slip)

        venting_gas = self.find_output_stream("gas")
        venting_gas.copy_flow_rates_from(input)
        venting_gas.subtract_gas_rates_from(gas_to_flare)
        venting_gas.subtract_gas_rates_from(methane_slip)

        #energy-use
        energy_use = self.energy
        # emissions
        emissions = self.emissions

        emissions.add_from_stream(EM_FLARING, gas_to_flare)
        emissions.add_from_stream(EM_FLARING, methane_slip)
        pass




