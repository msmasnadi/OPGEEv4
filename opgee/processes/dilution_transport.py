from ..emissions import EM_COMBUSTION
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL, EN_RESID
from ..log import getLogger
from ..process import Process
from ..transport_energy import TransportEnergy
from .shared import get_energy_carrier

_logger = getLogger(__name__)


class DiluentTransport(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.oil = field.oil
        self.API_diluent = field.attr("diluent_API")
        self.transport_share_fuel = field.model.transport_share_fuel
        self.transport_parameter = field.model.transport_parameter
        self.transport_by_mode = field.model.transport_by_mode
        self.diluent_transport_share_fuel = self.transport_share_fuel.loc["Diluent"]
        self.diluent_transport_parameter = self.transport_parameter[["Diluent", "Units"]]
        self.diluent_transport_by_mode = self.transport_by_mode.loc["Diluent"]

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("oil for transport")

        if input.is_uninitialized():
            return

        oil_mass_rate = input.liquid_flow_rate("oil")
        oil_mass_energy_density = self.oil.mass_energy_density(self.API_diluent)
        oil_LHV_rate = oil_mass_rate * oil_mass_energy_density

        # energy use
        energy_use = self.energy
        fuel_consumption = TransportEnergy.get_transport_energy_dict(self.field,
                                                                     self.diluent_transport_parameter,
                                                                     self.diluent_transport_share_fuel,
                                                                     self.diluent_transport_by_mode,
                                                                     oil_LHV_rate)

        for name, value in fuel_consumption.items():
            energy_use.set_rate(get_energy_carrier(name), value.to("mmBtu/day"))

        # emission
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission.to("tonne/day"))

    def impute(self):
        output = self.find_output_stream("oil for dilution")
        input = self.find_input_stream("oil for transport")
        input.copy_flow_rates_from(output)


