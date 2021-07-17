from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID, PHASE_GAS
from opgee import ureg
from ..energy import Energy, EN_NATURAL_GAS, EN_ELECTRICITY, EN_UPG_PROC_GAS, EN_PETCOKE
from ..emissions import EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES

_logger = getLogger(__name__)


class HeavyOilUpgrading(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.oil = self.field.oil
        self.water = self.field.water
        self.upgrader_gas_comp = self.attrs_with_prefix("upgrader_gas_comp_")
        self.oil_sand_mine = self.attr("oil_sands_mine")
        self.fraction_elec_onsite = field.attr("fraction_elec_onsite")
        self.cogeneration_upgrading = self.attr("cogeneration_upgrading")
        self.NG_heating_value = self.model.const("NG-heating-value")
        self.petro_coke_heating_value = self.model.const("petrocoke-heating-value")
        self.mole_to_scf = self.model.const("mol-per-scf")
        self.upgrader_type = self.field.attr("upgrader_type")

    def run(self, analysis):
        self.print_running_msg()

        if self.field.attr("crude_oil_dewatering_output") != self.name:
            self.enabled = False
            return

        heavy_oil_upgrading_table = self.field.model.heavy_oil_upgrading[self.upgrader_type]

        # mass rate
        input_oil = self.find_input_streams("oil for upgrading", combine=True)
        input_gas = self.find_input_stream("gas for upgrading")

        upgrading_insitu = True if self.upgrader_type is not None and self.oil_sand_mine != "Without upgrader" else False
        upgrader_process_gas_MW = (self.upgrader_gas_comp * self.oil.component_MW[self.upgrader_gas_comp.index]).sum()
        upgrader_process_gas_heating_value = (self.upgrader_gas_comp *
                                              self.oil.component_LHV_molar[self.upgrader_gas_comp.index] *
                                              self.mole_to_scf).sum()

        oil_mass_rate = input_oil.liquid_flow_rate("oil")  # TODO: if upgrading_insitu else oil_vol_rate
        oil_vol_rate = oil_mass_rate / (self.oil.oil_specific_gravity * self.water.density())
        SCO_bitumen_ratio = heavy_oil_upgrading_table["SCO/bitumen ratio"].values[0]
        SCO_output = oil_vol_rate * SCO_bitumen_ratio

        coke_yield = ureg.Quantity(heavy_oil_upgrading_table["Coke yield per bbl SCO output"].values[0], "kg/bbl_oil")
        coke_generation = SCO_output * coke_yield
        coke_to_heat = coke_generation * heavy_oil_upgrading_table["Coke yield per bbl SCO output"][
            "Fraction coke to self use - Heating"]
        coke_to_stockpile_and_transport = coke_generation - coke_to_heat

        proc_gas_yield = ureg.Quantity(heavy_oil_upgrading_table["Process gas (PG) yield per bbl SCO output"].values[0],
                                       "scf/bbl_oil")
        proc_gas_to_heat = SCO_output * proc_gas_yield * \
                           heavy_oil_upgrading_table["Process gas (PG) yield per bbl SCO output"][
                               "Fraction PG to self use - Heating (W/O cogen)"]
        proc_gas_to_H2 = SCO_output * proc_gas_yield * \
                         heavy_oil_upgrading_table["Process gas (PG) yield per bbl SCO output"][
                             "Fraction PG to self use - H2 gen"]
        proc_gas_exported = SCO_output * proc_gas_yield * \
                            heavy_oil_upgrading_table["Process gas (PG) yield per bbl SCO output"][
                                "Fraction PG exported"]
        proc_gas_flared = SCO_output * proc_gas_yield * \
                          heavy_oil_upgrading_table["Process gas (PG) yield per bbl SCO output"]["Fraction PG flared"]

        output_proc_gas = self.find_output_stream("process gas")
        proc_gas_mass_rate = (self.upgrader_gas_comp *
                              self.oil.component_MW[self.upgrader_gas_comp.index] *
                              proc_gas_exported *
                              self.mole_to_scf)
        output_proc_gas.set_rates_from_series(proc_gas_mass_rate, PHASE_GAS)

        electricity_yield = ureg.Quantity(heavy_oil_upgrading_table["Electricity intensity"].values[0], "kWh/bbl_oil")
        frac_electricity_self_gene = self.fraction_elec_onsite * self.cogeneration_upgrading
        elect_cogen = SCO_output * frac_electricity_self_gene * electricity_yield
        elect_import = SCO_output * electricity_yield * (1 - frac_electricity_self_gene)

        NG_intensity = ureg.Quantity(heavy_oil_upgrading_table["Natural gas intensity (W/O cogen)"].values[0],
                                     "scf/bbl_oil")
        NG_to_cogen_yield = frac_electricity_self_gene * electricity_yield / \
                            heavy_oil_upgrading_table["Cogen turbine efficiency"].values[0] / self.NG_heating_value
        NG_to_H2 = NG_intensity * SCO_output * heavy_oil_upgrading_table["Natural gas intensity (W/O cogen)"][
            "Fraction NG - H2"]
        NG_to_cogen = NG_to_cogen_yield * SCO_output
        heat_from_cogen = NG_to_cogen * self.NG_heating_value * \
                          heavy_oil_upgrading_table["Cogeneration steam efficiency"].values[0]
        NG_to_heat = max(SCO_output * NG_intensity * heavy_oil_upgrading_table["Natural gas intensity (W/O cogen)"][
            "Fraction NG - Heating (W/O cogen)"] -
                         heat_from_cogen / upgrader_process_gas_heating_value, 0)

        # energy use
        energy_use = self.energy
        NG_consumption = (NG_to_cogen + NG_to_H2 + NG_to_heat) * self.NG_heating_value
        upgrader_process_gas_consumption = (proc_gas_to_H2 + proc_gas_flared + proc_gas_to_heat) * self.NG_heating_value
        petro_coke_consumption = coke_to_heat * self.petro_coke_heating_value
        energy_use.set_rate(EN_NATURAL_GAS, NG_consumption.to("mmBtu/day"))
        energy_use.set_rate(EN_UPG_PROC_GAS, upgrader_process_gas_consumption.to("mmBtu/day"))
        energy_use.set_rate(EN_PETCOKE, petro_coke_consumption.to("mmBtu/day"))
        energy_use.set_rate(EN_ELECTRICITY, elect_import.to("mmBtu/day"))

        # emission
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combusion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "CO2", combusion_emission)
        proc_gas_flaring_rate = (self.upgrader_gas_comp *
                                 self.oil.component_MW[self.upgrader_gas_comp.index] *
                                 proc_gas_flared *
                                 self.mole_to_scf)

        # TODO: check this with Adam. The E153 under Heavy Oil Upgrading does not seem right
        emissions.add_from_series(EM_FLARING, proc_gas_flaring_rate)
        pass
