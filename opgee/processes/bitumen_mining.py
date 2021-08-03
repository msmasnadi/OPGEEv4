from ..process import Process
from ..log import getLogger
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_UPG_PROC_GAS, EN_PETCOKE, EN_DIESEL
from ..emissions import EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES
from ..error import OpgeeException, AbstractMethodError, OpgeeStopIteration
from opgee import ureg
from ..stream import PHASE_LIQUID, PHASE_GAS

_logger = getLogger(__name__)


class BitumenMining(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.oil = field.oil
        self.API_bitumen = field.attr("API_bitumen")
        self.bitumen_SG = self.oil.specific_gravity(self.API_bitumen)
        self.temperature_mined_bitumen = field.attr("temperature_mined_bitumen")
        self.pressure_mined_bitumen = field.attr("pressure_mined_bitumen")
        self.oil_sands_mine = field.attr("oil_sands_mine")
        self.gas_comp = field.attrs_with_prefix("gas_comp_")

        self.FOR = field.attr("FOR")
        self.VOR = field.attr("VOR")

        self.water = self.field.water
        self.water_density = self.water.density()

    def run(self, analysis):
        self.print_running_msg()

        if self.oil_sands_mine == "None":
            self.enabled = False
            return

        # mass rate
        input = self.find_input_stream("oil")
        bitumen_mass_rate = input.liquid_flow_rate("oil")
        bitumen_volume_rate = bitumen_mass_rate / self.bitumen_SG / self.water_density

        d = self.model.mining_energy_intensity

        mining_intensity_table = d[self.oil_sands_mine]
        unit_col = d["Units"]

        mine_flaring_rate = self.FOR * bitumen_volume_rate * self.gas_comp * self.model.const("mol-per-scf") * \
                            self.oil.component_MW[self.gas_comp.index]
        mine_offgas_rate = self.VOR * bitumen_volume_rate * self.gas_comp * self.model.const("mol-per-scf") * \
                           self.oil.component_MW[self.gas_comp.index]

        gas_fugitives = self.find_output_stream("gas fugitive")
        gas_fugitives.set_rates_from_series(mine_offgas_rate, PHASE_GAS)

        gas_flaring = self.find_output_stream("gas flaring")
        gas_flaring.set_rates_from_series(mine_flaring_rate, PHASE_GAS)

        # energy-use
        energy_use = self.energy
        NG_consumption = bitumen_volume_rate * ureg.Quantity(mining_intensity_table["Natural gas use"],
                                                             unit_col["Natural gas use"]) * self.model.const(
            "NG-heating-value")
        diesel_consumption = bitumen_volume_rate * ureg.Quantity(mining_intensity_table["Diesel fuel use"],
                                                                 unit_col["Diesel fuel use"]) * self.model.const(
            "diesel-LHV")
        electricity_consumption = bitumen_volume_rate * ureg.Quantity(mining_intensity_table["Electricity use"],
                                                                      unit_col["Electricity use"])
        energy_use.set_rate(EN_NATURAL_GAS, NG_consumption.to("mmBtu/day"))
        energy_use.set_rate(EN_DIESEL, diesel_consumption.to("mmBtu/day"))
        energy_use.set_rate(EN_ELECTRICITY, electricity_consumption.to("mmBtu/day"))

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        if self.process_EF is None:
            raise OpgeeException(f"{self.name} does not have emission factor")
        combusion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "CO2", combusion_emission)

        emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)

    def impute(self):

        input_dilution = self.find_output_stream("oil for dilution")

        oil_mass_rate = input_dilution.liquid_flow_rate("oil")
        input = self.find_input_stream("oil")
        input.set_liquid_flow_rate("oil", oil_mass_rate, self.temperature_mined_bitumen, self.pressure_mined_bitumen)
