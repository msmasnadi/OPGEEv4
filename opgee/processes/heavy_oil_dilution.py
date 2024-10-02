#
# HeavyOilDilution class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..core import TemperaturePressure
from ..emissions import EM_COMBUSTION
from ..import_export import DILUENT
from ..process import Process
from ..processes.transport_energy import TransportEnergy
from .shared import get_energy_carrier


class HeavyOilDilution(Process):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.water_density = self.water.density()

        model = self.model
        self.transport_share_fuel = model.transport_share_fuel.loc["Diluent"]
        self.transport_parameter = model.transport_parameter[["Diluent", "Units"]]
        self.transport_by_mode = model.transport_by_mode.loc["Diluent"]

        self.before_diluent_tp = None
        self.bitumen_tp = None
        self.dilbit_API = None
        self.dilbit_SG = None
        self.diluent_API = None
        self.diluent_tp = None
        self.dilution_SG = None
        self.dilution_type = None
        self.downhole_pump = None
        self.final_mix_tp = None
        self.frac_diluent = None
        self.oil_sands_mine = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field

        self.frac_diluent = self.attr("fraction_diluent")
        self.downhole_pump = field.downhole_pump
        self.oil_sands_mine = field.oil_sands_mine

        self.bitumen_tp = TemperaturePressure(field.mined_bitumen_t,
                                              field.mined_bitumen_p)

        self.diluent_API = self.attr("diluent_API")
        self.dilution_SG = self.oil.specific_gravity(self.diluent_API)
        self.dilbit_API = self.attr("dilbit_API")
        self.dilbit_SG = self.oil.specific_gravity(self.dilbit_API)

        self.dilution_type = self.attr("dilution_type")
        self.diluent_tp = TemperaturePressure(self.attr("diluent_temp"),
                                              self.attr("diluent_temp"))
        self.before_diluent_tp = TemperaturePressure(self.attr("before_diluent_temp"),
                                                     self.attr("before_diluent_press"))
        self.final_mix_tp = TemperaturePressure(self.attr("final_mix_temp"),
                                                self.attr("final_mix_press"))

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        # mass rate
        input_oil = self.find_input_streams("oil for dilution", combine=True)

        # TODO: need to raise error message
        # if self.frac_diluent.m == 0.0:
        #     return

        if input_oil.is_uninitialized():
            return

        input_liquid_mass_rate = input_oil.liquid_flow_rate("oil")
        oil_SG = field.oil.specific_gravity(input_oil.API)
        input_liquid_volume_rate = input_liquid_mass_rate / (oil_SG * self.water_density)

        frac_diluent = self.frac_diluent
        expected_volume_oil_bitumen = input_liquid_volume_rate if abs(frac_diluent.to("frac").m - 1) <= 0.01 else \
            input_liquid_volume_rate / (1 - frac_diluent)
        required_volume_diluent = expected_volume_oil_bitumen * frac_diluent

        if self.dilution_type == "Diluent":
            required_mass_dilution = required_volume_diluent * self.dilution_SG * self.water_density
            total_mass_diluted_oil = required_mass_dilution + input_liquid_mass_rate
            diluent_LHV = field.oil.mass_energy_density(API=self.diluent_API)
        else:
            total_mass_diluted_oil = expected_volume_oil_bitumen * self.dilbit_SG * self.water_density
            required_mass_dilution = total_mass_diluted_oil if frac_diluent == 1 else \
                max(0, total_mass_diluted_oil - input_liquid_mass_rate)
            diluent_SG = required_mass_dilution / required_volume_diluent / self.water_density
            diluent_LHV = field.oil.mass_energy_density(API=field.oil.API_from_SG(diluent_SG))

        output_oil = self.find_output_stream("oil for storage", raiseError=False)
        if output_oil is None:
            output_oil = self.find_output_stream("oil for upgrading")
        output_oil.set_liquid_flow_rate("oil", total_mass_diluted_oil, tp=self.final_mix_tp)
        self.set_iteration_value(output_oil.total_flow_rate())

        field.save_process_data(final_diluent_LHV_mass=diluent_LHV)

        final_diluent_SG = \
            total_mass_diluted_oil / expected_volume_oil_bitumen / self.water_density
        final_diluent_API = field.oil.API_from_SG(final_diluent_SG)
        output_oil.set_API(final_diluent_API)

        diluent_energy_rate = required_mass_dilution * diluent_LHV

        # Calculate imported diluent energy consumption
        fuel_consumption = field.transport_energy.get_transport_energy_dict(self.field,
                                                                            self.transport_parameter,
                                                                            self.transport_share_fuel,
                                                                            self.transport_by_mode,
                                                                            diluent_energy_rate,
                                                                            "Diluent")

        energy_use = self.energy
        for name, value in fuel_consumption.items():
            energy_use.set_rate(get_energy_carrier(name), value.to("mmBtu/day"))

        # import/export
        import_product = field.import_export
        self.set_import_from_energy(energy_use)
        import_product.set_export(self.name, DILUENT, diluent_energy_rate)

        # emission
        combustion_emission = self.compute_emission_combustion()
        self.emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)
