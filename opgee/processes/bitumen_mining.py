#
# BitumenMining class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .. import ureg
from ..core import TemperaturePressure
from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
from ..log import getLogger
from ..process import Process
from ..stream import Stream
from ..error import OpgeeException

_logger = getLogger(__name__)


class BitumenMining(Process):
    """
    This process takes ... do ...

    input streams:
        - (optional)

    output streams:
        - (optional)

    field data stored:
        -
    """

    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()

        self.oil_sands_mine = field.attr("oil_sands_mine")
        if self.oil_sands_mine == "None":
            # TODO: move this to the run() method
            self.set_enabled(False)
            return

        self.oil = field.oil
        self.API_bitumen = field.attr("API")
        self.bitumen_SG = self.oil.specific_gravity(self.API_bitumen)

        self.mined_bitumen_tp = TemperaturePressure(field.attr("temperature_mined_bitumen"),
                                                    field.attr("pressure_mined_bitumen"))
        self.downhole_pump = field.attr("downhole_pump")
        self.oil_prod_rate = field.attr("oil_prod")
        self.upgrader_type = field.attr("upgrader_type")
        self.gas_comp = field.attrs_with_prefix("gas_comp_")
        self.FOR = field.attr("FOR")
        self.VOR = field.attr("VOR")
        self.bitumen_path_dict = {"Integrated with upgrader": "bitumen for upgrading",
                                  "Integrated with diluent": "bitumen for dilution",
                                  "Integrated with both": "bitumen for dilution"}

        self.water = self.field.water
        self.water_density = self.water.density()
        self.CH4_loss_rate = self.attr("CH4_loss_rate")

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        bitumen_mass_rate = self.oil_prod_rate * self.bitumen_SG * self.water_density
        try:
            output = self.bitumen_path_dict[self.oil_sands_mine]
        except:
            raise OpgeeException(f"{self.name} bitumen is not recognized:{self.oil_sands_mine}."
                                 f"Must be one of {list(self.bitumen_path_dict.keys())}")
        output_bitumen = self.find_output_stream(output)

        output_tp = self.mined_bitumen_tp
        output_bitumen.set_liquid_flow_rate("oil", bitumen_mass_rate, tp=output_tp)
        self.set_iteration_value(output_bitumen.total_flow_rate())

        d = self.model.mining_energy_intensity

        mining_intensity_table = d[self.oil_sands_mine]
        unit_col = d["Units"]

        temp = self.oil_prod_rate * field.gas.component_gas_rho_STP["C1"]
        mine_flaring_rate = self.FOR * temp
        mine_CH4_rate = self.CH4_loss_rate * temp

        gas_fugitives = Stream("gas_fugitives", tp=field.stp)
        gas_fugitives.set_gas_flow_rate("C1", mine_CH4_rate)

        gas_flaring = self.find_output_stream("gas for partition")
        gas_flaring.set_gas_flow_rate("C1", mine_flaring_rate)
        gas_flaring.set_tp(field.stp)

        # energy-use
        energy_use = self.energy
        NG_consumption = \
            self.oil_prod_rate * ureg.Quantity(mining_intensity_table["Natural gas use"],
                                               unit_col["Natural gas use"]) * self.model.const("NG-heating-value")
        diesel_consumption = \
            self.oil_prod_rate * ureg.Quantity(mining_intensity_table["Diesel fuel use"],
                                               unit_col["Diesel fuel use"]) * self.model.const("diesel-LHV")
        electricity_consumption = \
            self.oil_prod_rate * ureg.Quantity(mining_intensity_table["Electricity use"], unit_col["Electricity use"])
        energy_use.set_rate(EN_NATURAL_GAS, NG_consumption.to("mmBtu/day"))
        energy_use.set_rate(EN_DIESEL, diesel_consumption.to("mmBtu/day"))
        energy_use.set_rate(EN_ELECTRICITY, electricity_consumption.to("mmBtu/day"))

        # import/export
        self.set_import_from_energy(energy_use)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)

        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
