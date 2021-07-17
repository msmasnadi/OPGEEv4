from ..log import getLogger
from ..process import Process
from ..stream import Stream, PHASE_LIQUID


class HeavyOilDilution(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.oil = self.field.oil
        self.oil_SG = self.oil.oil_specific_gravity
        self.oil_prod_rate = field.attr("oil_prod")

        self.water = self.field.water
        self.water_density = self.water.density()

        self.frac_diluent = field.attr("fraction_diluent")
        self.downhole_pump = field.attr("downhole_pump")
        self.oil_sand_mine = self.attr("oil_sands_mine")
        self.API_bitumen = field.attr("API_bitumen")
        self.bitumen_SG = self.oil.specific_gravity(self.API_bitumen)
        self.dilution_type = self.attr("dilution_type")
        self.bitumen_temp = field.attr("temperature_mined_bitumen")
        self.bitumen_press = field.attr("pressure_mined_bitumen")
        self.API_dilution = self.attr("diluent_API")
        self.dilution_SG = self.oil.specific_gravity(self.API_dilution)
        self.before_diluent_temp = self.attr("before_diluent_temp")
        self.before_diluent_press = self.attr("before_diluent_press")

    def run(self, analysis):
        self.print_running_msg()

        # mass rate

        input = self.find_input_streams("oil for dilution", combine=True)

        total_mass_oil_bitumen_before_dilution = input.liquid_flow_rate("oil")
        final_SG = self.oil_SG if self.oil_sand_mine is None else self.bitumen_SG
        total_volume_oil_bitumen_before_dilution = 0 if self.frac_diluent == 1 else \
            total_mass_oil_bitumen_before_dilution / final_SG / self.water_density
        expected_volume_oil_bitumen = self.oil_prod_rate if self.frac_diluent == 1 else \
            self.oil_prod_rate / (1 - self.frac_diluent)
        required_volume_diluent = expected_volume_oil_bitumen if self.frac_diluent == 1 else \
            expected_volume_oil_bitumen * self.frac_diluent

        if self.dilution_type == "Diluent":
            required_mass_dilution = required_volume_diluent * self.dilution_SG * self.water_density
            total_mass_diluted_oil = required_mass_dilution + total_mass_oil_bitumen_before_dilution
        else:
            total_mass_diluted_oil = expected_volume_oil_bitumen * self.dilution_SG
            required_mass_dilution = total_mass_diluted_oil if self.frac_diluent == 1 else \
                total_mass_diluted_oil - total_mass_oil_bitumen_before_dilution
        diluted_oil_bitumen_SG = self.oil_SG if expected_volume_oil_bitumen <= 0 else \
            total_mass_diluted_oil / expected_volume_oil_bitumen / self.water_density

        input_streams = self.find_input_streams("oil for dilution")
        input_bitumen = input_streams["bitumen mining to heavy oil dilution"]
        input_bitumen_mass_rate = input_bitumen.liquid_flow_rate("oil")
        input_heavy_oil_mass_rate = total_mass_oil_bitumen_before_dilution - input_bitumen_mass_rate

        stream = Stream("diluent", temperature=self.before_diluent_temp, pressure=self.before_diluent_press)
        diluent_density = self.oil.density(stream, self.dilution_SG, self.oil.gas_specific_gravity,
                                           self.oil.gas_oil_ratio)
        heavy_oil_density = self.oil.density(stream, self.oil_SG, self.oil.gas_specific_gravity, self.oil.gas_oil_ratio)
        diluent_energy_density_mass = self.oil.mass_energy_density(API=self.API_dilution)
        heavy_oil_energy_density_mass = self.oil.mass_energy_density(API=self.oil.API)
        diluent_energy_density_vol = diluent_energy_density_mass * diluent_density
        heavy_oil_energy_density_vol = heavy_oil_energy_density_mass * heavy_oil_density

        final_diluent_LHV_vol = diluent_energy_density_vol if self.frac_diluent == 1.0 or self.dilution_type == "Diluent" else \
            (
                        diluent_energy_density_vol * expected_volume_oil_bitumen - total_volume_oil_bitumen_before_dilution * heavy_oil_energy_density_vol) / required_volume_diluent
        final_diluent_LHV_mass = diluent_energy_density_mass if self.frac_diluent == 1.0 or self.dilution_type == "Diluent" else \
            (
                        diluent_energy_density_vol * total_mass_diluted_oil - total_mass_oil_bitumen_before_dilution * heavy_oil_energy_density_vol) / required_mass_dilution

        # energy use
        energy_use = self.energy

        # emission
        emissions = self.emissions

    def impute(self):

        input = self.find_input_streams("oil for dilution")
        input_bitumen = input["bitumen mining to heavy oil dilution"]

        # mass rate
        upgrader_type = self.field.attr("upgrader_type")
        upgrader_mining_prod_offsite = 1 if (
                                                        self.oil_sand_mine is None or self.oil_sand_mine == "Non-integrated with upgrader") \
                                            and self.downhole_pump == 0 and upgrader_type is not None else 0
        bitumen_mass_rate = self.oil_prod_rate * self.bitumen_SG * self.water_density if upgrader_mining_prod_offsite == 0 and self.oil_sand_mine == "Non-integrated with upgrader" else 0
        input_bitumen.set_liquid_flow_rate("oil", bitumen_mass_rate, self.bitumen_temp, self.bitumen_press)
