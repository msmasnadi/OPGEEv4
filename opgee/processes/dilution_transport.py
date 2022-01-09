from ..emissions import EM_COMBUSTION
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL, EN_RESID
from ..log import getLogger
from ..process import Process
from ..transport_energy import TransportEnergy

_logger = getLogger(__name__)


class DiluentTransport(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.oil = field.oil
        self.API_diluent = field.attr("diluent_API")
        self.diluent_transport_share_fuel = field.model.diluent_transport_share_fuel
        self.diluent_transport_parameter = field.model.diluent_transport_parameter

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
                                                                     oil_LHV_rate)
        energy_use.set_rate(EN_NATURAL_GAS, fuel_consumption["Natural gas"].to("mmBtu/day"))
        energy_use.set_rate(EN_DIESEL, fuel_consumption["Diesel"].to("mmBtu/day"))
        energy_use.set_rate(EN_RESID, fuel_consumption["Residual oil"].to("mmBtu/day"))
        energy_use.set_rate(EN_ELECTRICITY, fuel_consumption["Electricity"].to("mmBtu/day"))

        # emission
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combusion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "CO2", combusion_emission)

    def impute(self):
        output = self.find_output_stream("oil for dilution")
        input = self.find_input_stream("oil for transport")
        input.copy_flow_rates_from(output)


