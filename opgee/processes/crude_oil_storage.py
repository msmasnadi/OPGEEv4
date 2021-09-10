from ..process import Process
from ..log import getLogger
from ..stream import Stream, PHASE_LIQUID, PHASE_GAS
from ..emissions import EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES
from opgee import ureg

_logger = getLogger(__name__)


class CrudeOilStorage(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.oil = field.oil
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")
        self.tonne_to_bbl = field.model.const("tonne-to-bbl")
        self.storage_gas_comp = self.attrs_with_prefix("storage_gas_comp_")
        self.CH4_comp = self.attr("storage_gas_comp_C1")
        self.f_FG_CS_VRU = self.attr("f_FG_CS_VRU")
        self.f_FG_CS_FL = self.attr("f_FG_CS_FL")
        self.oil_sands_mine = field.attr("oil_sands_mine")

    def run(self, analysis):
        self.print_running_msg()

        #TODO: LPG to blend with crude oil need to be implement after gas branch

        # mass rate
        input = self.find_input_streams("oil for storage", combine=True)
        oil_mass_rate = input.liquid_flow_rate("oil")
        # TODO: loss rate need to be replaced by VF-component
        loss_rate = self.venting_fugitive_rate()
        loss_rate = ureg.Quantity(0.47, "kg/bbl_oil")
        gas_exsolved_upon_flashing = oil_mass_rate * loss_rate * self.tonne_to_bbl / \
                                     self.CH4_comp if self.oil_sands_mine == "None" else ureg.Quantity(0, "tonne/day")

        vapor_to_flare = self.f_FG_CS_FL * gas_exsolved_upon_flashing * self.storage_gas_comp
        vapor_to_VRU = self.f_FG_CS_VRU * gas_exsolved_upon_flashing * self.storage_gas_comp
        gas_fugitives = (1 - self.f_FG_CS_VRU - self.f_FG_CS_FL) * gas_exsolved_upon_flashing * self.storage_gas_comp

        output_flare = self.find_output_stream("gas for flaring")
        output_flare.set_rates_from_series(vapor_to_flare, PHASE_GAS)
        output_flare.set_temperature_and_pressure(self.std_temp, self.std_press)

        output_VRU = self.find_output_stream("gas for VRU")
        output_VRU.set_rates_from_series(vapor_to_VRU, PHASE_GAS)
        output_VRU.set_temperature_and_pressure(self.std_temp, self.std_press)

        gas_fugitive_stream = self.find_output_stream("gas fugitives")
        gas_fugitive_stream.set_rates_from_series(gas_fugitives, PHASE_GAS)
        gas_fugitive_stream.set_temperature_and_pressure(self.std_temp, self.std_press)

        # No energy-use for storage

        # emissions
        emissions = self.emissions
        emissions.add_from_stream(EM_FUGITIVES, gas_fugitive_stream)

