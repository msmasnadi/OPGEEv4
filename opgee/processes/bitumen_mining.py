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
    # TODO: documentation below describes input streams that do not appear in the code.
    """
        This process takes input streams and produces output streams as part of an
        oil sands mining operation.

        Inputs:
            - Streams from bitumen path dictionary

        Outputs:
            - Bitumen stream for upgrading or dilution
            - Gas stream for partition

        Attributes:
            - oil_sands_mine: Name of the oil sands mine
            - API_bitumen: API gravity of the bitumen
            - bitumen_SG: Specific gravity of the bitumen
            - mined_bitumen_tp: Temperature and pressure of the mined bitumen
            - oil_prod_rate: Oil production rate
            - upgrader_type: Type of upgrader used
            - gas_comp: Gas composition
            - FOR: Flaring oil ratio
            - VOR: Venting oil ratio
            - bitumen_path_dict: Dictionary of possible paths for the bitumen stream
            - water_density: Density of water
            - CH4_loss_rate: Methane loss rate
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self._required_outputs = []

        self._required_outputs = [
            # TODO: If the process names were avoided, we might have just one output stream
            #  with, say, "heavy oil". Should describe the contents, not the destination.
            ("oil for upgrading",     # TODO: avoid process names in contents.
             "oil for dilution"),     # TODO: avoid process names in contents.

            "gas for partition",
        ]


        self.bitumen_path_dict = {"Integrated with upgrader": "oil for upgrading",
                                  "Integrated with diluent": "oil for dilution",
                                  "Integrated with both": "oil for dilution"}
        self.water_density = self.water.density()

        self.CH4_loss_rate = None
        self.FOR = None
        self.bitumen_SG = None
        self.downhole_pump = None
        self.gas_comp = None
        self.mined_bitumen_p = None
        self.mined_bitumen_t = None
        self.mined_bitumen_tp = None
        self.oil_sands_mine = None
        self.oil_volume_rate = None
        self.upgrader_type = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field

        self.oil_sands_mine = field.oil_sands_mine
        self.bitumen_SG = self.oil.specific_gravity(field.attr("API"))

        self.mined_bitumen_t = field.mined_bitumen_t
        self.mined_bitumen_p = field.mined_bitumen_p
        self.mined_bitumen_tp = TemperaturePressure(self.mined_bitumen_t,
                                                    self.mined_bitumen_p)
        self.downhole_pump = field.downhole_pump
        self.oil_volume_rate = field.oil_volume_rate
        self.upgrader_type = field.upgrader_type
        self.gas_comp = field.gas_comp
        self.FOR = field.FOR

        self.CH4_loss_rate = self.attr("CH4_loss_rate")

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        bitumen_mass_rate = self.oil_volume_rate * self.bitumen_SG * self.water_density
        try:
            output = self.bitumen_path_dict[self.oil_sands_mine]
        except:
            raise OpgeeException(f"{self.name} bitumen is not recognized:{self.oil_sands_mine}."
                                 f"Must be one of {list(self.bitumen_path_dict.keys())}")
        output_bitumen = self.find_output_stream(output)

        output_tp = self.mined_bitumen_tp
        output_bitumen.\
            set_liquid_flow_rate("oil", bitumen_mass_rate, tp=output_tp)
        output_bitumen.set_API(field.attr("API"))
        self.set_iteration_value(output_bitumen.total_flow_rate())

        d = self.model.mining_energy_intensity
        mining_intensity_table = d[self.oil_sands_mine]
        unit_col = d["Units"]

        temp = self.oil_volume_rate * field.gas.component_gas_rho_STP["C1"]
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
            self.oil_volume_rate * ureg.Quantity(mining_intensity_table["Natural gas use"],
                                                 unit_col["Natural gas use"]) * self.model.const("NG-heating-value")
        diesel_consumption = \
            self.oil_volume_rate * ureg.Quantity(mining_intensity_table["Diesel fuel use"],
                                                 unit_col["Diesel fuel use"]) * self.model.const("diesel-LHV")
        electricity_consumption = \
            self.oil_volume_rate * ureg.Quantity(mining_intensity_table["Electricity use"], unit_col["Electricity use"])
        energy_use.set_rate(EN_NATURAL_GAS, NG_consumption.to("mmBtu/day"))
        energy_use.set_rate(EN_DIESEL, diesel_consumption.to("mmBtu/day"))
        energy_use.set_rate(EN_ELECTRICITY, electricity_consumption.to("mmBtu/day"))

        # import and export
        self.set_import_from_energy(energy_use)

        # emissions
        combustion_emission = self.compute_emission_combustion()
        self.emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)

        self.emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
