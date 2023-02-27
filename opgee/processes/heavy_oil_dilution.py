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
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.oil = self.field.oil
        self.oil_SG = self.oil.oil_specific_gravity
        self.oil_prod_rate = field.attr("oil_prod")

        self.water = self.field.water
        self.water_density = self.water.density()

        self.frac_diluent = self.attr("fraction_diluent")
        self.downhole_pump = field.attr("downhole_pump")
        self.oil_sand_mine = field.attr("oil_sands_mine")

        self.bitumen_API = field.attr("API")
        self.bitumen_SG = self.oil.specific_gravity(self.bitumen_API)
        self.bitumen_tp = TemperaturePressure(field.attr("temperature_mined_bitumen"),
                                              field.attr("pressure_mined_bitumen"))

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

        self.transport_share_fuel = self.model.transport_share_fuel.loc["Diluent"]
        self.transport_parameter = self.model.transport_parameter[["Diluent", "Units"]]
        self.transport_by_mode = self.model.transport_by_mode.loc["Diluent"]

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        # mass rate
        input_oil = self.find_input_stream("oil for dilution", raiseError=False)
        input_bitumen = self.find_input_stream("bitumen for dilution", raiseError=False)

        if self.frac_diluent.m == 0.0:
            return

        if input_oil is None and input_bitumen is None:
            return

        if (input_oil is not None and input_oil.is_uninitialized()) and \
                (input_bitumen is not None and input_bitumen.is_uninitialized()):
            return

        if input_oil:
            input_liquid_mass_rate = input_oil.liquid_flow_rate("oil")
            input_liquid_SG = self.oil.oil_specific_gravity
        elif input_bitumen:
            input_liquid_mass_rate = input_bitumen.liquid_flow_rate("oil")
            input_liquid_SG = self.bitumen_SG

        frac_diluent = self.frac_diluent
        input_liquid_vol_rate = input_liquid_mass_rate / input_liquid_SG / self.water_density
        expected_volume_oil_bitumen = input_liquid_vol_rate if abs(frac_diluent - 1) <= 0.01 else \
            input_liquid_vol_rate / (1 - frac_diluent)
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

        self.field.save_process_data(final_diluent_LHV_mass=diluent_LHV)
        diluent_energy_rate = required_mass_dilution * diluent_LHV

        # Calculate imported diluent energy consumption
        fuel_consumption = TransportEnergy.get_transport_energy_dict(self.field,
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
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)
