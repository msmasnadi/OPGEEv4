from ..emissions import EM_COMBUSTION
from ..log import getLogger
from ..process import Process
from opgee.processes.transport_energy import TransportEnergy
from .shared import get_energy_carrier
from ..import_export import ImportExport, CRUDE_OIL

_logger = getLogger(__name__)


class CrudeOilTransport(Process):
    """
    Crude oil transport calculate emissions from crude oil to the market

    """

    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.oil = field.oil
        self.transport_share_fuel = field.transport_share_fuel.loc["Crude"]
        self.transport_parameter = field.transport_parameter[["Crude", "Units"]]
        self.transport_by_mode = field.transport_by_mode.loc["Crude"]

    def run(self, analysis):
        self.print_running_msg()

        input_oil = self.find_input_stream("oil for transport")

        if input_oil.is_uninitialized():
            return

        oil_mass_rate = input_oil.liquid_flow_rate("oil")
        oil_mass_energy_density = self.oil.mass_energy_density()
        oil_LHV_rate = oil_mass_rate * oil_mass_energy_density

        if self.field.get_process_data("crude_LHV") is None:
            self.field.save_process_data(crude_LHV=oil_mass_energy_density)

        output = self.find_output_stream("oil for refinery")
        output.copy_flow_rates_from(input_oil)

        # energy use
        energy_use = self.energy
        fuel_consumption = TransportEnergy.get_transport_energy_dict(self.field,
                                                                     self.transport_parameter,
                                                                     self.transport_share_fuel,
                                                                     self.transport_by_mode,
                                                                     oil_LHV_rate,
                                                                     "Crude")

        for name, value in fuel_consumption.items():
            energy_use.set_rate(get_energy_carrier(name), value.to("mmBtu/day"))

        # import/export
        import_product = ImportExport()
        import_product.set_import_from_energy(self.name, energy_use)
        import_product.set_export(self.name, CRUDE_OIL, oil_LHV_rate)

        # emission
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)