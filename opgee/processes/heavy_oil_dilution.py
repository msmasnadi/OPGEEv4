from .. import ureg
from ..core import TemperaturePressure
from ..process import Process
from ..stream import Stream


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

        self.bitumen_API = field.attr("API_bitumen")
        self.bitumen_SG  = self.oil.specific_gravity(self.bitumen_API)
        self.bitumen_tp  = TemperaturePressure(field.attr("temperature_mined_bitumen"),
                                               field.attr("pressure_mined_bitumen"))

        self.diluent_API = self.attr("diluent_API")
        self.dilution_SG = self.oil.specific_gravity(self.diluent_API)

        self.dilution_type = self.attr("dilution_type")
        self.diluent_tp        = TemperaturePressure(self.attr("diluent_temp"),
                                                     self.attr("diluent_temp"))
        self.before_diluent_tp = TemperaturePressure(self.attr("before_diluent_temp"),
                                                     self.attr("before_diluent_press"))
        self.final_mix_tp      = TemperaturePressure(self.attr("final_mix_temp"),
                                                     self.attr("final_mix_press"))

    def run(self, analysis):
        self.print_running_msg()

        if self.frac_diluent.m == 0.0 or not self.all_streams_ready("oil for dilution"):
            return

        # mass rate
        input = self.find_input_streams("oil for dilution", combine=True)

        if input.is_uninitialized():
            return

        output = self.find_output_stream("oil for storage")
        total_mass_rate = input.liquid_flow_rate("oil")
        output.set_liquid_flow_rate("oil", total_mass_rate, TP=self.final_mix_tp)

    def impute(self):

        input_streams = self.find_input_streams("oil for dilution")

        # TODO: reliance on stream names is very brittle. Look for stream content instead.
        if "bitumen mining to heavy oil dilution" in input_streams:
            input_bitumen = input_streams["bitumen mining to heavy oil dilution"]
            bitumen_mass_rate = self.get_bitumen_mass_rate()
            input_bitumen.set_liquid_flow_rate("oil", bitumen_mass_rate.to("tonne/day"), tp=self.bitumen_tp)

        input = self.find_input_streams("oil for dilution", combine=True)

        frac_diluent = self.frac_diluent

        total_mass_oil_bitumen_before_dilution = input.liquid_flow_rate("oil")
        final_SG = self.oil_SG if self.oil_sand_mine is None else self.bitumen_SG
        total_volume_oil_bitumen_before_dilution = 0 if frac_diluent == 1 else \
            total_mass_oil_bitumen_before_dilution / final_SG / self.water_density
        expected_volume_oil_bitumen = self.oil_prod_rate if frac_diluent == 1 else \
            self.oil_prod_rate / (1 - frac_diluent)
        required_volume_diluent = expected_volume_oil_bitumen if frac_diluent == 1 else \
            expected_volume_oil_bitumen * frac_diluent

        if self.dilution_type == "Diluent":
            required_mass_dilution = required_volume_diluent * self.dilution_SG * self.water_density
            total_mass_diluted_oil = required_mass_dilution + total_mass_oil_bitumen_before_dilution
        else:
            total_mass_diluted_oil = expected_volume_oil_bitumen * self.dilution_SG
            required_mass_dilution = total_mass_diluted_oil if frac_diluent == 1 else \
                total_mass_diluted_oil - total_mass_oil_bitumen_before_dilution

        # TODO: unused variable
        diluted_oil_bitumen_SG = self.oil_SG if expected_volume_oil_bitumen <= 0 else \
            total_mass_diluted_oil / expected_volume_oil_bitumen / self.water_density

        stream = Stream("diluent", self.before_diluent_tp)
        diluent_density = self.oil.density(stream, self.dilution_SG, self.oil.gas_specific_gravity,
                                           self.oil.gas_oil_ratio)
        heavy_oil_density = self.oil.density(stream, self.oil_SG, self.oil.gas_specific_gravity, self.oil.gas_oil_ratio)
        diluent_energy_density_mass = self.oil.mass_energy_density(API=self.diluent_API)
        heavy_oil_energy_density_mass = self.oil.mass_energy_density(API=self.oil.API)
        diluent_energy_density_vol = diluent_energy_density_mass * diluent_density
        heavy_oil_energy_density_vol = heavy_oil_energy_density_mass * heavy_oil_density

        # TODO: unused variable
        final_diluent_LHV_vol = diluent_energy_density_vol if frac_diluent == 1.0 or self.dilution_type == "Diluent" else \
            (diluent_energy_density_vol * expected_volume_oil_bitumen - total_volume_oil_bitumen_before_dilution * heavy_oil_energy_density_vol) / required_volume_diluent

        final_diluent_LHV_mass = diluent_energy_density_mass if frac_diluent == 1.0 or self.dilution_type == "Diluent" else \
            (diluent_energy_density_vol * total_mass_diluted_oil - total_mass_oil_bitumen_before_dilution * heavy_oil_energy_density_vol) / required_mass_dilution

        input_dilution_transport = input_streams["dilution transport to heavy oil dilution"]
        input_dilution_transport.set_liquid_flow_rate("oil", required_mass_dilution.to("tonne/day"), tp=self.diluent_tp)

        self.field.save_process_data(final_diluent_LHV_mass=final_diluent_LHV_mass)

    def get_bitumen_mass_rate(self):
        """
        Calculate bitumen mass rate

        :return:
        """
        upgrader_type = self.field.attr("upgrader_type")

        # TODO: Reliance on string matching is brittle. If a modeler changes a name, the code breaks.
        #       Rethink this. One option is to have a file that registers names that are relied on in the
        #       code and assigns them to "official" variable names so they are centralized and documented.
        non_integrated_with_upgrader = "Non-integrated with upgrader"

        upgrader_mining_prod_offsite = 1 if (self.oil_sand_mine is None or
                                             self.oil_sand_mine == non_integrated_with_upgrader) \
                                            and self.downhole_pump == 0 and upgrader_type is not None else 0

        bitumen_mass_rate = self.oil_prod_rate * self.bitumen_SG * self.water_density \
            if upgrader_mining_prod_offsite == 0 and \
               self.oil_sand_mine == non_integrated_with_upgrader else ureg.Quantity(0, "tonne/day")

        return bitumen_mass_rate



