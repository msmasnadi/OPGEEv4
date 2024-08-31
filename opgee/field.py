#
# Field class
#
# Author: Richard Plevin and Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import networkx as nx
import pint
import pandas as pd

from . import ureg
from .config import getParamAsList
from .constants import (
    SIMPLE_RESULT,
    DETAILED_RESULT,
    ERROR_RESULT,
    DEFAULT_RESULT_TYPE,
    USER_RESULT_TYPES,
    ALL_RESULT_TYPES,
)
from .container import Container
from .core import elt_name, instantiate_subelts, dict_from_list, STP, magnitude
from .energy import Energy
from .error import (
    OpgeeException,
    OpgeeStopIteration,
    OpgeeMaxIterationsReached,
    OpgeeIterationConverged,
    ModelValidationError,
    ZeroEnergyFlowError,
)
from .import_export import ImportExport
from .log import getLogger
from .process import Process, Aggregator, Reservoir, decache_subclasses
from .process_groups import ProcessChoice
from .processes.steam_generator import SteamGenerator
from .processes.transport_energy import TransportEnergy
from .smart_defaults import SmartDefault
from .stream import Stream
from .thermodynamics import Oil, Gas, Water
from .utils import getBooleanXML, roundup
from .combine_streams import combine_streams
from .bfs import bfs

_logger = getLogger(__name__)


class FieldResult:
    def __init__(
            self,
            analysis_name,
            field_name,
            result_type,
            energy_data=None,
            ghg_data=None,  # CO2e
            gas_data=None,  # individual gases
            streams_data=None,
            ci_results=None,
            trial_num=None,
            error=None,
    ):
        self.analysis_name = analysis_name
        self.field_name = field_name
        self.result_type = result_type
        self.ci_results = ci_results  # list of tuples of (node_name, CI)
        self.energy = energy_data
        self.emissions = ghg_data  # TBD: change self.emissions to self.ghgs
        self.gases = gas_data
        self.streams = streams_data
        self.trial_num = trial_num
        self.error = error

    def __str__(self):
        trl = "" if self.trial_num is None else f"trl:{self.trial_num} "
        return f"<{self.__class__.__name__} ana:{self.analysis_name} fld:{self.field_name} {trl}err:{self.error} res:{self.result_type}>"


def total_emissions(proc, gwp):
    rates = proc.emissions.rates(gwp)
    total = rates.loc["GHG"].sum()
    return total


class Field(Container):
    """
    A `Field` contains all the `Process` instances associated with a single oil or
    gas field, and the `Stream` instances that connect them. It also holds an instance
    of `Reservoir`, which is a source (it has outputs only), in the process structure.

    Fields can contain mutually exclusive process choice sets that group processes to
    be enabled or disabled together as a coherent group. The "active" set is determimed
    by the value of attributes named the same as the `<ProcessChoice>` element.

    See {opgee}/etc/attributes.xml for attributes defined for the `<Field>`.
    See also :doc:`OPGEE XML documentation <opgee-xml>`
    """

    def __init__(self, name, attr_dict=None, parent=None, group_names=None):
        super().__init__(name, attr_dict=attr_dict, parent=parent)

        self.model = model = self.find_container("Model")
        self.group_names = group_names or []

        self.stream_dict = None
        self.boundary_dict = {}
        self.process_choice_dict = None
        self.process_dict = None
        self.agg_dict = None

        # DOCUMENT: boundary names must be predefined, but can be set in configuration.
        #   Each name must appear 0 or 1 times, and at least one boundary must be defined.
        self.known_boundaries = set(getParamAsList("OPGEE.Boundaries"))

        # Each Field has one of these built-in processes
        self.reservoir = None  # set in add_children()

        # Additional builtin processes can be instantiated and added here if needed
        self.builtin_procs = None  # set in add_children()

        self.extend = False

        # Stores the name of a Field that the current field copies then modifies
        # If a Field named X appears in an Analysis element, and specifies that it
        # modifies another Field Y, Field Y is copied and any elements defined within
        # Field X are merged into the copy, and the copy is added to the Model with the
        # new name. The "modifies" value is stored to record this behavior.
        self.modifies = None

        self.carbon_intensity = ureg.Quantity(0.0, "g/MJ")
        self.procs_beyond_boundary = None

        self.graph = None
        self.cycles = None

        # A "bulletin-board" to share data among processes, cleared in reset() method.
        self.process_data = {}

        self.wellhead_tp = None

        self.stp = STP

        self.component_fugitive_table = None
        self.loss_mat_gas_ave_df = None

        self.import_export = ImportExport()

        self.oil = Oil(self)
        self.gas = Gas(self)
        self.water = Water(self)

        # TODO: Why are these copied into the Field object? Why not access them from Model?
        # TODO: It's good practice to declare all instance vars in __init__ (set to None perhaps)
        #       other programmers (and PyCharm) recognize them as proper instance variables and
        #       not random values set in other methods.
        self.upstream_CI = model.upstream_CI
        self.vertical_drill_df = model.vertical_drill_df
        self.horizontal_drill_df = model.horizontal_drill_df
        self.imported_gas_comp = model.imported_gas_comp

        self.LNG_temp = model.const("LNG-temp")

        # declare instance vars to IDE knows about them
        self.AGR_feedin_press = None
        self.API = None
        self.depth = None
        self.distance_survey = None
        self.downhole_pump = None
        self.ecosystem_richness = None
        self.eta_rig = None
        self.field_development_intensity = None
        self.field_production_lifetime = None
        self.flood_gas_type = None
        self.FOR = None
        self.frac_CO2_breakthrough = None
        self.frac_water_reinj = None
        self.frac_wells_horizontal = None
        self.fraction_elec_onsite = None
        self.fraction_remaining_gas_inj = None
        self.fraction_steam_cogen = None
        self.fraction_steam_solar = None
        self.fraction_wells_fractured = None
        self.friction_factor = None
        self.friction_loss_steam_distr = None
        self.gas_comp = None
        self.gas_flooding = None
        self.gas_lifting = None
        self.gas_oil_ratio = None
        self.gas_path = None
        self.GOR = None
        self.GFIR = None
        self.GLIR = None
        self.length_lateral = None
        self.mined_bitumen_p = None
        self.mined_bitumen_t = None
        self.natural_gas_reinjection = None
        self.natural_gas_to_liquefaction_frac = None
        self.num_prod_wells = None
        self.num_water_inj_wells = None
        self.num_gas_inj_wells = None
        self.number_wells_dry = None
        self.number_wells_exploratory = None
        self.offshore = None
        self.oil_path = None
        self.oil_sands_mine = None
        self.oil_volume_rate = None
        self.pipe_leakage = None
        self.pressure_gradient_fracturing = None
        self.prod_tubing_diam = None
        self.productivity_index = None
        self.reflux_ratio = None
        self.regeneration_feed_temp = None
        self.res_press = None
        self.res_temp = None
        self.SOR = None
        self.stab_gas_press = None
        self.steam_flooding = None
        self.upgrader_type = None
        self.volume_per_well_fractured = None
        self.frac_venting = None
        self.water_flooding = None
        self.water_reinjection = None
        self.weight_land_survey = None
        self.weight_ocean_survey = None
        self.well_complexity = None
        self.well_size = None
        self.wellhead_t = None
        self.wellhead_p = None
        self.WIR = None
        self.WOR = None
        self.transport_energy = None
        self.steam_generator = None

        # Cache attribute values and call initializers that depend on them
        self.cache_attributes()

    def cache_attributes(self):
        self.AGR_feedin_press = self.attr("AGR_feedin_press")
        self.API = self.attr("API")
        self.depth = self.attr("depth")
        self.distance_survey = self.attr("distance_survey")
        self.downhole_pump = self.attr("downhole_pump")
        self.ecosystem_richness = self.attr("ecosystem_richness")
        self.eta_rig = self.attr("eta_rig")
        self.field_development_intensity = self.attr("field_development_intensity")
        self.field_production_lifetime = self.attr("field_production_lifetime")
        self.flood_gas_type = self.attr("flood_gas_type")
        self.FOR = self.attr("FOR")
        self.frac_CO2_breakthrough = self.attr("frac_CO2_breakthrough")
        self.frac_water_reinj = self.attr("fraction_water_reinjected")
        self.frac_wells_horizontal = self.attr("fraction_wells_horizontal")
        self.fraction_elec_onsite = self.attr("fraction_elec_onsite")
        self.fraction_remaining_gas_inj = self.attr("fraction_remaining_gas_inj")
        self.fraction_steam_cogen = self.attr("fraction_steam_cogen")
        self.fraction_steam_solar = self.attr("fraction_steam_solar")
        self.fraction_wells_fractured = self.attr("fraction_wells_fractured")
        self.friction_factor = self.attr("friction_factor")
        self.friction_loss_steam_distr = self.attr("friction_loss_steam_distr")
        self.gas_comp = self.attrs_with_prefix("gas_comp_")
        self.gas_flooding = self.attr("gas_flooding")
        self.gas_lifting = self.attr("gas_lifting")
        self.gas_oil_ratio = self.attr("GOR")
        self.gas_path = self.attr("gas_processing_path")
        self.GOR = self.attr("GOR")
        self.GFIR = self.attr("GFIR")
        self.GLIR = self.attr("GLIR")
        self.length_lateral = self.attr("length_lateral")
        self.mined_bitumen_p = self.attr("pressure_mined_bitumen")
        self.mined_bitumen_t = self.attr("temperature_mined_bitumen")
        self.natural_gas_reinjection = self.attr("natural_gas_reinjection")
        self.natural_gas_to_liquefaction_frac = self.attr("natural_gas_to_liquefaction_frac")
        self.num_prod_wells = self.attr("num_prod_wells")
        self.num_water_inj_wells = self.attr("num_water_inj_wells")
        self.num_gas_inj_wells = self.attr("num_gas_inj_wells")
        self.number_wells_dry = self.attr("number_wells_dry")
        self.number_wells_exploratory = self.attr("number_wells_exploratory")
        self.offshore = self.attr("offshore")
        self.oil_path = self.attr("oil_processing_path")
        self.oil_sands_mine = self.attr("oil_sands_mine")
        self.oil_volume_rate = self.attr("oil_prod")
        self.pipe_leakage = self.attr("surface_piping_leakage")
        self.pressure_gradient_fracturing = self.attr("pressure_gradient_fracturing")
        self.prod_tubing_diam = self.attr("well_diam")
        self.productivity_index = self.attr("prod_index")
        self.reflux_ratio = self.attr("reflux_ratio")
        self.regeneration_feed_temp = self.attr("regeneration_feed_temp")
        self.res_press = self.attr("res_press")
        self.res_temp = self.attr("res_temp")
        self.SOR = self.attr("SOR")
        self.stab_gas_press = self.attr("gas_pressure_after_boosting")
        self.steam_flooding = self.attr("steam_flooding")
        self.upgrader_type = self.attr("upgrader_type")  # used only in smart default
        self.volume_per_well_fractured = self.attr("volume_per_well_fractured")
        self.frac_venting = self.attr("frac_venting")
        self.water_flooding = self.attr("water_flooding")
        self.water_reinjection = self.attr("water_reinjection")
        self.weight_land_survey = self.attr("weight_land_survey")
        self.weight_ocean_survey = self.attr("weight_ocean_survey")
        self.well_complexity = self.attr("well_complexity")
        self.well_size = self.attr("well_size")
        self.ocean_tanker_size = self.attr("ocean_tanker_size")

        # Add wellhead tp to the smart default
        self.wellhead_t = min(self.res_temp, self.attr("wellhead_temperature"))
        self.wellhead_p = min(self.res_press, self.attr("wellhead_pressure"))
        self.WIR = self.attr("WIR")
        self.WOR = self.attr("WOR")

        self.transport_energy = TransportEnergy(self)  # N.B. accesses field.SOR
        self.steam_generator = SteamGenerator(self)

    # Used by validate() to descend model hierarchy
    def _children(self):
        return (
            super()._children()
        )  # + self.streams() # Adding this caused several errors...

    def add_children(
            self, aggs=None, procs=None, streams=None, process_choice_dict=None
    ):
        # Note that `procs` include only Processes defined at the top-level of the field.
        # Other Processes maybe defined within the Aggregators in `aggs`.
        super().add_children(aggs=aggs, procs=procs)

        # Each Field has one of these built-in processes
        self.reservoir = Reservoir(parent=self)

        # Additional builtin processes can be instantiated and added here if needed
        self.builtin_procs = [self.reservoir]

        self.stream_dict = dict_from_list(streams)

        known_boundaries = self.known_boundaries

        # Remember streams that declare themselves as system boundaries. Keys must be one of the
        # values in the tuples in the _known_boundaries dictionary above. s
        boundary_dict = self.boundary_dict

        # Save references to boundary processes by name; fail if duplicate definitions are found.
        for proc in procs:
            boundary = proc.boundary
            if boundary:
                if boundary not in known_boundaries:
                    raise OpgeeException(
                        f"{self}: {proc} boundary {boundary} is not a known boundary name. Must be one of {known_boundaries}"
                    )

                other = boundary_dict.get(boundary)
                if other:
                    raise OpgeeException(
                        f"{self}: Duplicate declaration of boundary '{boundary}' in {proc} and {other}"
                    )

                boundary_dict[boundary] = proc
                # _logger.debug(f"{self}: {proc} defines boundary '{boundary}'")

        self.process_choice_dict = process_choice_dict

        all_procs = self.collect_processes()  # includes Reservoir
        self.process_dict = self.adopt(all_procs, asDict=True)

        self.agg_dict = {agg.name: agg for agg in self.descendant_aggs()}

        self.check_attr_constraints(self.attr_dict)

        (
            self.component_fugitive_table,
            self.loss_mat_gas_ave_df,
        ) = self.get_component_fugitive()

        self.finalize_process_graph()

    def finalize_process_graph(self):
        """
        Apply Smart Defaults and resolve process choices, which may depend on values
        of Smart Defaults. This can modify the process structure by including or
        excluding process groups, so we do this before computing the process network
        graph.

        :return: nothing
        """
        # The analysis arg now defaults to None, which means we've lost the ability to
        # have defaults that depend on Analysis attributes, e.g., "Analysis.gwp_horizon".
        # TODO: decide whether to give up that feature and drop analysis keyword
        SmartDefault.apply_defaults(self)
        self.resolve_process_choices()  # allows smart defaults to set process choices

        # we use networkx to reason about the directed graph of Processes (nodes)
        # and Streams (edges).
        self.graph = g = self._connect_processes()

        self.cycles = list(nx.simple_cycles(g))
        # if self.cycles:
        #     _logger.debug(f"Field '{self.name}' has cycles: {self.cycles}")

    # TBD: write test
    def _check_run_after_procs(self):
        """
        For procs tagged 'after="True"', allow outputs only to other "after" procs.
        """

        def _run_after_ok(proc):
            for dst in proc.successors():
                if not dst.run_after:
                    return False
            return True

        bad = [
            proc
            for proc in self.processes()
            if proc.run_after and not _run_after_ok(proc)
        ]
        if bad:
            # DOCUMENT after=True attribute
            raise OpgeeException(
                f"Processes {bad} are tagged 'after=True' but have output streams to non-'after' processes"
            )

        return True

    def __str__(self):
        return f"<Field '{self.name}'>"

    def _impute(self):
        # recursive helper function
        def _impute_upstream(proc):
            # recurse upstream, calling impute(), but don't cycle
            if proc and proc.enabled and not proc.visited():
                proc.visit()
                proc.impute()

                upstream_procs = {
                    stream.src_proc for stream in proc.inputs if stream.impute
                }
                for upstream_proc in upstream_procs:
                    _impute_upstream(upstream_proc)

        start_streams = self.find_start_streams()

        for stream in start_streams:
            if not stream.impute:
                raise OpgeeException(
                    f"A start stream {stream} cannot have its 'impute' flag set to '0'."
                )

        # Find procs with start == True or find start_procs upstream from streams with exogenous data.from
        # We require that all start streams emerge from one Process.
        start_procs = {p for p in self.processes() if p.impute_start} or {
            stream.src_proc for stream in start_streams
        }

        start_count = len(start_procs)
        # No impute
        if start_count == 0:
            return

        if start_count != 1:
            procs = f": {start_procs}" if start_count else ""

            raise OpgeeException(
                f"Expected one start process upstream from start streams, got {len(start_procs)}{procs}"
            )

        start_proc = start_procs.pop()
        _logger.debug(f"Running impute() for {start_proc}")

        try:
            _impute_upstream(start_proc)
        except OpgeeStopIteration:
            # Shouldn't be possible
            raise OpgeeException(
                "Impute failed due to a process loop. Use Stream attribute impute='0' to break cycle."
            )

    def run(self, analysis, compute_ci=True, trial_num=None):
        """
        Run all Processes defined for this Field, in the order computed from the graph
        characteristics, using the settings in `analysis` (e.g., GWP).

        :param analysis: (Analysis) the `Analysis` to use for analysis-specific settings.
        :param compute_ci: (bool) if False, CI calculation is not performed (used by some tests)
        :param trial_num: (int) the trial number, if running in MCS mode. This is used only for
            logging purposes.
        :return: None
        """
        from .core import Timer

        if self.is_enabled():
            timer = Timer("field.run")

            trial_str = f"trial {trial_num} of " if trial_num is not None else ""
            _logger.info(f"Running {trial_str}'{self.name}'")

            self.check_enabled_processes()

            # Cache the sets of processes within and outside the current boundary. We use
            # this information in compute_carbon_intensity() to ignore irrelevant procs.
            boundary_proc = self.boundary_process(analysis)
            self.procs_beyond_boundary = boundary_proc.beyond_boundary()

            self.reset()
            self._impute()
            self.reset_iteration()
            self.run_processes(analysis)

            self.check_balances()

            # Perform aggregations
            self.get_energy_rates()

            self.get_emission_rates(
                analysis, procs_to_exclude=self.procs_beyond_boundary
            )
            self.carbon_intensity = (
                self.compute_carbon_intensity(analysis) if compute_ci else None
            )
            _logger.info(timer.stop())

    def reset(self):
        self.reset_streams()
        self.reset_processes()
        # TODO: self.process_data.clear()

        # TODO: figure out why this breaks all tests for processes that
        #  look for process data named "processing_unit_loss_rate_df".
        #  That data is stored only in gas_gathering.py (run method).
        #  It appears that maintaining this data between Field runs is
        #  required for some reason. Seems like a stale cache bug.
        #
        # self.process_data.clear()

        SmartDefault.decache()
        decache_subclasses()

    def reset_iteration(self):
        Process.clear_iterating_process_list()
        for proc in self.processes():
            proc.reset_iteration()

    def reset_processes(self):
        for proc in self.processes():
            proc.reset()  # also resets iteration

    def reset_streams(self):
        for stream in self.streams():
            # If a stream is disabled, leave it so. (self.streams() returns only enabled streams.)
            # Otherwise, disable it if either of its source or destination processes is disabled.
            if not (stream.src_proc.enabled and stream.dst_proc.enabled):
                stream.set_enabled(False)

            stream.reset()

    def check_balances(self):
        for p in self.processes():
            p.check_balances()

    def boundary_processes(self):
        boundary_procs = [proc for proc in self.processes() if proc.boundary]
        return boundary_procs

    def boundary_process(self, analysis) -> Process:
        """
        Return the currently chosen boundary process.

        :return: (opgee.Process) the currently chosen boundary process
        """
        try:
            return self.boundary_dict[analysis.boundary]
        except KeyError:
            raise OpgeeException(
                f"{self} does not declare boundary process '{analysis.boundary}'."
            )

    def defined_boundaries(self):
        """
        Return the names of all boundaries defined in configuration system)
        """
        return self.known_boundaries

    def boundary_energy_flow_rate(self, analysis, raiseError=True):
        """
        Return the energy flow rate for the user's chosen system boundary, functional unit
        (oil vs gas)

        :param analysis: (Analysis) the analysis this field is part of
        :param raiseError: (bool) whether to raise an error if the energy flow is zero at the boundary
        :return: (pint.Quantity) the energy flow at the boundary
        """
        boundary_proc = self.boundary_process(analysis)
        combined_stream = combine_streams(boundary_proc.inputs)

        # TODO: Add method to calculate petcoke energy flow rate
        energy = self.oil.energy_flow_rate(combined_stream) + self.gas.energy_flow_rate(
            combined_stream
        )

        if energy.m == 0:
            if raiseError:
                raise ZeroEnergyFlowError(boundary_proc)
            else:
                _logger.warning(
                    f"Zero energy flow rate for {boundary_proc.boundary} boundary process {boundary_proc}"
                )

        return energy

    def compute_carbon_intensity(self, analysis):
        """
        Compute carbon intensity by summing emissions from all processes within the
        selected system boundary and dividing by the flow of the functional unit
        across that boundary stream.

        :param analysis: (Analysis) the analysis this field is part of
        :return: (pint.Quantity) carbon intensity in units of g CO2e/MJ
        """
        rates = self.emissions.rates(analysis.gwp)
        onsite_emissions = rates.loc["GHG"].sum()
        net_import = self.get_net_imported_product()
        imported_emissions = self.get_imported_emissions(net_import)
        total_emissions = onsite_emissions + imported_emissions

        # TODO: add option for displacement method
        # fn_unit = NATURAL_GAS if analysis.fn_unit == 'gas' else CRUDE_OIL
        # byproduct_names = self.product_names.drop(fn_unit)
        # byproduct_carbon_credit = self.get_carbon_credit(byproduct_names, analysis)
        # total_emissions = onsite_emissions + imported_emissions - byproduct_carbon_credit
        # energy = self.boundary_energy_flow_rate(analysis)

        # export_df = self.import_export.export_df
        # export_LHV = export_df.drop(columns=["Water"]).sum(axis='columns').sum()
        # self.carbon_intensity = ci = (total_emissions / export_LHV).to('grams/MJ')
        boundary_energy_flow_rate = self.boundary_energy_flow_rate(analysis)
        self.carbon_intensity = ci = ureg.Quantity(0, "grams/MJ")
        if boundary_energy_flow_rate.m != 0:
            self.carbon_intensity = ci = (
                    total_emissions / boundary_energy_flow_rate
            ).to("grams/MJ")

        return ci

    def partial_ci_values(self, analysis, nodes):
        """
        Compute partial CI for each node in ``nodes``, skipping boundary nodes, since
        these have no emissions and serve only to identify the endpoint for CI
        calculation.

        :param analysis: (opgee.Analysis)
        :param nodes: (list of Processes and/or Containers)
        :return: A list of tuples of (item_name, partial_CI)
        """
        from .error import ZeroEnergyFlowError
        from .process import Boundary

        try:
            energy = self.boundary_energy_flow_rate(analysis)

        except ZeroEnergyFlowError:
            _logger.error(
                f"Can't save results: zero energy flow at system boundary for {self}"
            )
            return None

        def partial_ci(obj):
            ghgs = obj.emissions.data.sum(axis="columns")["GHG"]
            if not isinstance(ghgs, pint.Quantity):
                ghgs = ureg.Quantity(ghgs, "tonne/day")

            ci = ghgs / energy
            # convert to g/MJ, but we don't need units in CSV file
            return ci.to("grams/MJ")

        results = [
            (obj.name, partial_ci(obj))
            for obj in nodes
            if not isinstance(obj, Boundary)
        ]
        return results

    def energy_and_emissions(self, analysis):
        import pandas as pd
        def process_data(proc_dict, column_name):
            data = pd.Series(proc_dict).apply(lambda x: x.m)

            # TODO: Extracts units from first element in the dict, which
            #  assumes all elements have the same units.
            unit = next(iter(proc_dict.values())).u

            # TODO: embedding units in the column name makes it difficult to use
            #  the units programmatically.
            df = pd.DataFrame(data, columns=[f'{column_name} ({unit})'])
            df.index.rename('process', inplace=True)
            return df

        gwp = analysis.gwp
        procs = self.processes()

        # Energy data processing
        energy_by_proc = {proc.name: proc.energy.rates().sum() for proc in procs}
        energy_data = process_data(energy_by_proc, self.name)

        # GHG data processing
        ghgs_by_proc = {proc.name: total_emissions(proc, gwp) for proc in procs}
        ghg_data = process_data(ghgs_by_proc, self.name)

        # TBD: create a more detailed csv file with ProcessName, and emission categories
        #  [EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES, EM_OTHER] as
        #  remaining columns, and species ['VOC', 'CO', 'CH4', 'N2O', 'CO2', 'GHG'] as rows.
        #  So basically, adding a column to each Emissions dataframe with the name of the
        #  process, then concatenating them into a dataframe.
        def gas_df_with_name(proc):
            from copy import copy

            df = proc.emissions.data.reset_index().rename(columns={"index": "gas"})
            cols = ['field', 'process'] + list(df.columns)
            df['field'] = self.name
            df['process'] = proc.name
            df = df[cols].pint.dequantify()  # move units to 2nd row of column headings...
            return df

        gases_by_proc = [gas_df_with_name(proc) for proc in procs]
        gases_data = pd.concat(gases_by_proc)

        return energy_data, ghg_data, gases_data

    def get_result(self, analysis, result_type, trial_num=None) -> FieldResult:
        """
        Collect results according to ``result_type``

        :param analysis: (Analysis) the analysis this field is part of
        :param result_type: (str) whether to return detailed or simple results. Legal values
            are DETAILED_RESULT or SIMPLE_RESULT.
        :param trial_num: (int) trial number, if running in MCS mode
        :return: (FieldResult) results
        """
        energy_data, ghg_data, gas_data = (
            self.energy_and_emissions(analysis)
            if result_type == DETAILED_RESULT
            else (None, None, None)
        )

        nodes = self.processes() if DETAILED_RESULT else self.children()
        ci_tuples = self.partial_ci_values(analysis, nodes)

        ci_results = (
            None
            if ci_tuples is None
            else [("TOTAL", self.carbon_intensity)] + ci_tuples
        )

        streams = self.streams()

        streams_data = pd.concat([s.to_dataframe() for s in streams])

        # TBD: need to save the streams data to CSV
        #  =========================================

        result = FieldResult(
            analysis.name,
            self.name,
            result_type,
            trial_num=trial_num,
            ci_results=ci_results,
            energy_data=energy_data,
            ghg_data=ghg_data,  # TBD: superseded by gas_data
            gas_data=gas_data,
            streams_data=streams_data,
        )
        return result

    def get_imported_emissions(self, net_import):
        """
        Calculate imported product emissions based on the upstream CI from GREET1_2016

        :param net_import: (Pandas.Series) net import energy rates (water is mass rate)
        :return: total emissions (units of g CO2)
        """
        from .import_export import WATER, N2, CO2_Flooding

        imported_emissions = ureg.Quantity(0.0, "tonne/day")

        for product, energy_rate in net_import.items():
            # TODO: Water, N2, and CO2 flooding is not in self.upstream_CI and not in upstream-CI.csv,
            #  which has units of g/mmbtu
            if product == WATER or product == N2 or product == CO2_Flooding:
                continue

            energy_rate = (
                energy_rate
                if isinstance(energy_rate, pint.Quantity)
                else ureg.Quantity(energy_rate, "mmbtu/day")
            )

            if energy_rate.m > 0:
                imported_emissions += energy_rate * self.upstream_CI.loc[product, "EF"]

        return imported_emissions

    # TODO Is this function deprecated or just not used yet?
    def get_carbon_credit(self, byproduct_names, analysis):
        """
        Calculate carbon credit from byproduct used for displacement co-production method

        :param net_import: (Pandas.Series) net import energy rates (water is mass rate)
        :return: total emissions (units of g CO2)
        """

        carbon_credit = ureg.Quantity(0.0, "tonne/day")
        export = self.import_export.export_df
        process_names = set(export.index)
        for name in byproduct_names:
            process_name = self.product_boundaries.loc[name, analysis.boundary]
            if process_name and process_name in process_names:
                carbon_credit += (
                        export.loc[process_name, name] * self.upstream_CI.loc[name, "EF"]
                )

        return carbon_credit

    @staticmethod
    def comp_fugitive_productivity(prod_mat_gas, mean):
        """
        Given field mean, find the value in the gas productivity table

        :param mean:
        :param prod_mat_gas:
        :return:
        """
        result = prod_mat_gas[
            (prod_mat_gas["Bin low"] < mean) & (prod_mat_gas["Bin high"] >= mean)
            ].index.values.astype(int)[0]

        return result

    @staticmethod
    def comp_fugitive_loss(loss_mat_ave, assignment):
        """
        Given assignment, find the loss rate in the loss rate table

        :param loss_mat_ave:
        :param assignment:
        :return:
        """
        return loss_mat_ave.iloc[assignment - 1, :]

    def get_component_fugitive(self):
        """
        Calculate loss rate for downhole pump, separation, and crude oil storage using Jeff's component fugitive model

        :return: (Pandas.Series) Process unit loss rate
        """
        model = self.model
        GOR = self.attr("GOR")
        GOR_cutoff = self.attr("GOR_cutoff")
        oil_rate = self.attr("oil_prod")
        productivity = oil_rate * (GOR + self.attr("gas_lifting") * self.attr("GLIR"))
        frac_wells_with_plunger = self.attr("frac_wells_with_plunger").m
        frac_wells_with_non_plunger = self.attr("frac_wells_with_non_plunger").m

        if self.attr("gas_flooding") and self.attr("flood_gas_type") == "CO2":
            productivity += (
                    oil_rate * self.attr("GFIR") * self.attr("frac_CO2_breakthrough")
            )

        num_prod_wells = self.attr("num_prod_wells")
        separation_loss_rate = ureg.Quantity(0.0, "frac")
        tank_loss_rate = ureg.Quantity(0.0, "frac")
        pump_loss_rate = ureg.Quantity(0.0, "frac")
        loss_mat_gas_ave_df = pd.DataFrame()

        if num_prod_wells > 0:
            productivity /= num_prod_wells

            productivity = productivity.to("kscf/day").m

            loss_mat_gas = model.loss_matrix_gas
            loss_mat_oil = model.loss_matrix_oil
            prod_mat_gas = model.productivity_gas
            prod_mat_oil = model.productivity_oil

            field_productivity = pd.DataFrame(
                columns=[
                    "Assignment",
                    "col_shift",
                    "Mean gas rate (Mscf/well/day)",
                    "Frac total gas",
                ],
                index=prod_mat_gas.index,
            )

            field_productivity["Mean gas rate (Mscf/well/day)"] = (
                prod_mat_gas["Normalized rate"]
                if GOR > GOR_cutoff
                else prod_mat_oil["Normalized rate"]
            )
            field_productivity["Mean gas rate (Mscf/well/day)"] *= productivity

            field_productivity["Frac total gas"] = (
                prod_mat_gas["Frac total gas"]
                if GOR > GOR_cutoff
                else prod_mat_oil["Frac total gas"]
            )

            field_productivity["Assignment"] = field_productivity.apply(
                lambda row: self.comp_fugitive_productivity(
                    prod_mat_gas, row["Mean gas rate (Mscf/well/day)"]
                ),
                axis=1,
            )

            # TBD: this has a hidden dependency on the tables' column names. Possible to compute this instead?
            common_cols = [
                "Well",
                "Header",
                "Heater",
                "Separator",
                "Meter",
                "Tanks-leaks",
                "Tank-thief hatch",
                "Recip Comp",
                "Dehydrator",
                "Chem Inj Pump",
                "Pneum Controllers",
                "Flash factor",
            ]
            cols_gas = common_cols + ["LU-plunger", "LU-no plunger"]
            cols_oil = common_cols
            tranch = range(10)
            flash_factor = 0.51  # kg CH4/bbl (total flashing gas). Divide by 0.51 to correct for fraction of wells controlled in Rutherford et al. 2021
            loss_mat_gas_ave = loss_mat_gas.mean(axis=0).values
            loss_mat_gas_ave = loss_mat_gas_ave.reshape(len(tranch), len(cols_gas))
            loss_mat_gas_ave_df = pd.DataFrame(
                data=loss_mat_gas_ave, index=prod_mat_gas["Bin low"], columns=cols_gas
            )

            cols = cols_gas if GOR > GOR_cutoff else cols_oil
            loss_mat = loss_mat_gas if GOR > GOR_cutoff else loss_mat_oil
            loss_mat_ave = loss_mat.mean(axis=0).values
            loss_mat_ave = loss_mat_ave.reshape(len(tranch), len(cols))
            df = pd.DataFrame(loss_mat_ave, columns=cols, index=range(len(tranch)))

            df = field_productivity.apply(
                lambda row: self.comp_fugitive_loss(df, row["Assignment"]), axis=1
            )
            comp_fugitive = df.T.dot(field_productivity["Frac total gas"])
            comp_fugitive["Flash factor"] /= flash_factor

            separation_loss_rate = comp_fugitive["Separator"]
            tank_loss_rate = comp_fugitive["Flash factor"]
            pump_loss_rate = comp_fugitive
            pump_loss_rate.drop(
                "Separator", inplace=True
            )  # TBD: drop both at same time
            pump_loss_rate.drop("Flash factor", inplace=True)

            if GOR > GOR_cutoff:
                pump_loss_rate["LU-plunger-norm"] = (
                        pump_loss_rate["LU-plunger"] * frac_wells_with_plunger
                        + pump_loss_rate["LU-no plunger"] * frac_wells_with_non_plunger
                )
                pump_loss_rate.drop(
                    "LU-plunger", inplace=True
                )  # TBD: drop both at same time
                pump_loss_rate.drop("LU-no plunger", inplace=True)
            pump_loss_rate = pump_loss_rate.sum()

            compressor_list = ["SourGasCompressor", "GasReinjectionCompressor"]
        # well_list = ["CO2InjectionWell", "GasReinjectionWell", "SourGasInjection"]

        process_loss_rate_dict = {
            "Separation": separation_loss_rate,
            "CrudeOilStorage": tank_loss_rate,
            "DownholePump": pump_loss_rate,
        }

        process_loss_rate = pd.Series(data=process_loss_rate_dict, dtype="pint[frac]")

        return process_loss_rate, loss_mat_gas_ave_df

    def get_completion_and_workover_C1_rate(self):
        """
        Calculate the total C1 rate for completion and workover events in a well system.

        This function takes into account the attributes 'is_flaring', 'is_REC', and 'frac_well_fractured'
        to determine the C1 rates for completion and workover events. The calculation uses a dataframe
        containing C1 rates for different scenarios of hydraulic fracturing, well type, flaring, and REC.

        Returns:
            float: The total C1 rate for completion and workover events in the well system.
        """
        oil_sands_mine = self.oil_sands_mine
        completion_event = (
            self.num_prod_wells
            if oil_sands_mine == "None"
            else ureg.Quantity(0, "frac")
        )
        workover_event = completion_event * self.attr("workovers_per_well")

        is_flaring = self.attr("is_flaring")
        is_REC = self.attr("is_REC")
        frac_well_fractured = self.attr("frac_well_fractured")
        df = self.model.well_completion_and_workover_C1_rate

        def find_value(df, is_hydraulic_fracture, well_type, is_flaring, is_REC):
            result = df.loc[
                (df["is_hydraulic_fracture"] == is_hydraulic_fracture)
                & (df["type"] == well_type)
                & (df["is_flaring"] == is_flaring)
                & (df["is_REC"] == is_REC)
                ]

            return (
                result["value"].values[0]
                if not result.empty
                else ureg.Quantity(0, "tonne")
            )

        def calculate_C1_rate(event, well_type):
            fracture_rate = find_value(df, "Yes", well_type, is_flaring, is_REC)
            no_fracture_rate = find_value(df, "No", well_type, is_flaring, "No")

            C1_rate = fracture_rate * frac_well_fractured + no_fracture_rate * (
                    1 - frac_well_fractured
            )
            return C1_rate * event

        completion_C1_rate = calculate_C1_rate(completion_event, "Completion")
        workover_C1_rate = calculate_C1_rate(workover_event, "Workover")

        return (completion_C1_rate + workover_C1_rate) / self.field_production_lifetime

    def validate(self):
        """
        Perform logical checks on the field after loading the entire model to ensure the field
        is "well-defined". This allows the processing code to avoid testing validity at run-time.
        Field conditions include:

        - Cycles cannot span the current boundary.
        - Aggregators cannot span the current boundary.
        - The chosen system boundary is defined for this field
        - Logical contradictions in attribute some settings

        :return: none
        :raises ModelValidationError: raised if any validation condition is violated.
        """
        super().validate()

        # Accumulate error msgs so user can correct them all at once.
        msgs = []

        try:
            self._check_run_after_procs()
        except OpgeeException as e:
            msgs.append(str(e))

        for proc in self.boundary_processes():
            # Cycles cannot span the current boundary. Test this by checking that the boundary
            # proc is not in any cycle. (N.B. __init__ evaluates and stores cycles.)

            # Check that there are Processes outside the current boundary. If not, nothing more to do.
            beyond = proc.beyond_boundary()
            if not beyond:
                continue

            for cycle in self.cycles:
                if proc in cycle:
                    msgs.append(
                        f"{proc.boundary} boundary {proc} is in one or more cycles."
                    )
                    break

            # There will generally be far fewer Processes outside the system boundary than within,
            # so we check that procs outside the boundary are not in Aggregators with members inside.
            aggs = self.descendant_aggs()
            for agg in aggs:
                procs = agg.descendant_procs()
                if not procs:
                    continue

                # See if first proc is inside or beyond the boundary, then make sure the rest are the same
                is_inside = procs[0] not in beyond
                is_beyond = not is_inside  # improves readability
                for proc in procs:
                    if (is_inside and proc in beyond) or (
                            is_beyond and proc not in beyond
                    ):
                        msgs.append(f"{agg} spans the {proc.boundary} boundary.")

        if self.attr("steam_flooding") and not self.attr("SOR"):
            msgs.append("SOR cannot be 0 when steam_flooding is chosen")

        if msgs:
            msg = "\n - ".join(msgs)
            raise ModelValidationError(f"Field validation failed: {msg}")

    def report(self, include_streams=False):
        """
        Print a text report showing Streams, energy, and emissions.
        """
        from .utils import dequantify_dataframe

        name = self.name

        if include_streams:
            _logger.debug(f"\n*** Streams for field '{name}'")
            for stream in self.streams():
                _logger.debug(
                    f"{stream} (tonne/day)\n{dequantify_dataframe(stream.components)}\n"
                )

        _logger.debug(f"{self}\nEnergy consumption:\n{self.energy.data}")
        _logger.debug(
            f"\nCumulative emissions to environment (tonne/day):\n{dequantify_dataframe(self.emissions.data)}"
        )
        _logger.debug(f"CI: {self.carbon_intensity:.2f}")

    def _is_cycle_member(self, process):
        """
        Return True if `process` is a member of any process cycle.

        :param process: (Process)
        :return: (bool)
        """
        return any([process in cycle for cycle in self.cycles])

    def _depends_on_cycle(self, process, visited=None):
        """
        Walk backwards (via input streams) and see if we encounter any
        node more than once, in which case ``process`` depends on a cycle.

        :param process: (opgee.Process) the Process that may depend on cycles.
        :param visited: (set) the Processes we've already encountered in our search.
        :return: (bool) True if ``process`` depends on any cycle, False otherwise.
        """

        visited = visited or set()

        for predecessor in process.predecessors():
            if predecessor in visited:
                return True

            visited.add(predecessor)
            if self._depends_on_cycle(predecessor, visited=visited):
                return True

        return False

    def _compute_graph_sections(self):
        """
        Divide the nodes of ``self.graph`` into four disjoint sets:
        1. Nodes neither in cycle nor dependent on cycles
        2. Nodes in cycles
        3. Nodes dependent on cycles
        4. Nodes tagged "after='true'" in the XML, sorted topologically

        :return: (4-tuple of sets of Processes)
        """
        processes = self.processes()

        # TODO: Wennan, I think the better fix here is to ensure that there are
        #   no disabled process in cycles.

        procs_in_cycles = set()
        reported = set()
        for cycle in self.cycles:
            for proc in cycle:
                if proc.is_enabled():
                    procs_in_cycles.add(proc)
                elif proc not in reported:
                    _logger.debug(f"Disabled proc {proc} is in one or more cycles")
                    reported.add(proc)  # so we report it only once

        cycle_dependent = set()

        if procs_in_cycles:
            for process in processes:
                if process not in procs_in_cycles and self._depends_on_cycle(process):
                    cycle_dependent.add(process)

        run_afters = {process for process in processes if process.run_after}

        cycle_independent = (
                set(processes) - procs_in_cycles - cycle_dependent - run_afters
        )
        return cycle_independent, procs_in_cycles, cycle_dependent, run_afters

    def check_enabled_processes(self):
        """
        Iterate all processes and allow them to check if they should be disabled before they run.
        """

        processes = self.processes()

        for proc in processes:
            proc.check_enabled()

    def run_processes(self, analysis):
        (
            cycle_independent,
            procs_in_cycles,
            cycle_dependent,
            run_afters,
        ) = self._compute_graph_sections()

        for proc in procs_in_cycles:
            proc.in_cycle = True

        # helper function
        def run_procs_in_order(processes):
            if not processes:
                return

            sg = self.graph.subgraph(processes)
            run_order = nx.topological_sort(sg)
            for proc in run_order:
                proc.run_if_enabled(analysis)

        # run all the cycle-independent nodes in topological order
        run_procs_in_order(cycle_independent)

        # If user has indicated a process with start-cycle="true", start there, otherwise
        # find a process with cycle-independent processes as inputs, and start there.
        start_procs = [proc for proc in procs_in_cycles if proc.cycle_start]

        if len(start_procs) > 1:
            raise OpgeeException(
                f"""Only one process can have cycle-start="true"; found {len(start_procs)}: {start_procs}"""
            )

        max_iter = self.model.maximum_iterations

        if procs_in_cycles:
            # Walk the cycle, starting at the indicated start process to generate an ordered list
            unvisited = procs_in_cycles.copy()
            start_proc = start_procs[0]
            import opgee  # TBD: what is this doing here?

            if any(isinstance(obj, Reservoir) for obj in unvisited):
                for obj in unvisited:
                    if isinstance(obj, Reservoir):
                        start_proc = obj
                        break

            if start_procs:
                ordered_cycle = []
                bfs(start_proc, unvisited, ordered_cycle)

                # add in any processes in cycles not reachable from the start proc
                for other in list(unvisited):
                    bfs(other, unvisited, ordered_cycle)

            else:
                # TBD: Compute ordering by looking for procs in cycle that are successors to
                #      cycle_independent procs. For now, just copy run using procs_in_cycles.
                ordered_cycle = procs_in_cycles

            # Iterate on the processes in cycle until a termination condition is met and an
            # OpgeeStopIteration exception is thrown, or we exceed max iterations.
            iter_count = 0
            while True:
                iter_count += 1
                if iter_count > max_iter:
                    raise OpgeeMaxIterationsReached(
                        f"Maximum iterations ({max_iter}) reached without convergence"
                    )

                try:
                    for proc in ordered_cycle:
                        proc.run_if_enabled(analysis)

                except OpgeeIterationConverged as e:
                    _logger.debug(e)
                    break

        # run all processes dependent on cycles, which are now complete
        run_procs_in_order(cycle_dependent)

        # finally, run all "after='True'" procs, in sort order
        run_procs_in_order(run_afters)

    def _connect_processes(self):
        """
        Connect streams and processes in a directed graph.

        :return: (networkx.DiGraph) a directed graph representing the processes and streams.
        """
        g = nx.MultiDiGraph()  # allows parallel edges

        # first add all defined Processes since some (Exploration, Development & Drilling)
        # have no streams associated with them, but we still need to run the processes.
        for p in self.processes():
            g.add_node(p)
            p.inputs.clear()  # since we append to inputs and outputs below
            p.outputs.clear()

        for s in self.streams():
            s.src_proc = src = self.find_process(s.src_name)
            s.dst_proc = dst = self.find_process(s.dst_name)

            if not (src.is_enabled() and dst.is_enabled()):
                disabled = []
                if not src.is_enabled():
                    disabled.append(src)

                if not dst.is_enabled():
                    disabled.append(dst)

                _logger.debug(f"{s} is connected to disabled processes: {disabled}")

            src.add_output_stream(s)
            dst.add_input_stream(s)

            g.add_edge(src, dst, stream=s)

        return g

    def streams(self):
        """
        Gets all enabled `Stream` instances for this `Field`.

        :return: (iterator of `Stream` instances) streams in this `Field`
        """
        return [s for s in self.stream_dict.values() if s.enabled]

    def processes(self):
        """
        Gets all instances of subclasses of `Process` for this `Field`.

        :return: (iterator of `Process` (subclasses) instances) in this `Field`
        """
        procs = [proc for proc in self.all_processes() if proc.is_enabled()]
        return procs

    def all_processes(self):
        """
        Gets all instances of subclasses of `Process` for this `Field`, including
        disabled Processes.

        :return: (iterator of `Process` (subclasses) instances) in this `Field`
        """
        return self.process_dict.values()

    # TBD: not used currently
    # def process_choice_node(self, name, raiseError=True):
    #     """
    #     Find a `ProcessChoice` instance by name.
    #
    #     :param name: (str) the name of the choice element
    #     :param raiseError: (bool) whether to raise an error if `name` is not found
    #     :return: (opgee.ProcessChoice) the instance found, or None
    #     """
    #     choice_node = self.process_choice_dict.get(name)
    #     if choice_node is None and raiseError:
    #         raise OpgeeException(f"Process choice '{name}' not found in field '{self.name}'")
    #
    #     return choice_node

    def find_stream(self, name, raiseError=True):
        """
        Find the Stream with `name` in this Field. If not found: if
        `raiseError` is True, an error is raised, else None is returned.

        :param name: (str) the name of the Stream to find
        :param raiseError: (bool) whether to raise an error if the Stream is not found.
        :return: (Stream or None) the requested Stream, or None if not found and `raiseError` is False.
        :raises: OpgeeException if `name` is not found and `raiseError` is True
        """
        stream = self.stream_dict.get(name)

        if stream is None and raiseError:
            raise OpgeeException(
                f"Stream named '{name}' was not found in field '{self.name}'"
            )

        return stream

    def find_process(self, name, raiseError=True):
        """
        Find the Process of class `name` in this Field. If not found: if
        `raiseError` is True, an error is raised, else None is returned.

        :param name: (str) the name of the subclass of Process to find
        :param raiseError: (bool) whether to raise an error if the Process is not found.
        :return: (Process or None) the requested Process, or None if not found and `raiseError` is False.
        :raises: OpgeeException if `name` is not found and `raiseError` is True
        """
        process = self.process_dict.get(name)

        if process is None and raiseError:
            raise OpgeeException(
                f"Process '{name}' was not found in field '{self.name}'"
            )

        return process

    def find_start_streams(self):
        streams = [s for s in self.streams() if s.has_exogenous_data]
        return streams

    def set_extend(self, value):
        self.extend = getBooleanXML(value)

    def set_modifies(self, modifies):
        self.modifies = modifies

    @classmethod
    def from_xml(cls, elt, parent=None):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Field> element
        :param parent: (opgee.Analysis) the Analysis containing the new Field
        :return: (Field) instance populated from XML
        """
        name = elt_name(elt)
        attrib = elt.attrib

        attr_dict = cls.instantiate_attrs(elt)
        group_names = [node.text for node in elt.findall("Group")]

        field = Field(name, attr_dict=attr_dict, parent=parent, group_names=group_names)

        field.set_enabled(attrib.get("enabled", "1"))
        field.set_extend(attrib.get("extend", "0"))
        field.set_modifies(
            attrib.get("modified")
        )  # "modified" attr is changed to "modified" after merging

        aggs = instantiate_subelts(elt, Aggregator, parent=field)
        procs = instantiate_subelts(elt, Process, parent=field)
        streams = instantiate_subelts(elt, Stream, parent=field)

        choices = instantiate_subelts(elt, ProcessChoice)
        # Convert to lowercase to avoid simple lookup errors
        process_choice_dict = {choice.name.lower(): choice for choice in choices}

        field.add_children(
            aggs=aggs,
            procs=procs,
            streams=streams,
            process_choice_dict=process_choice_dict,
        )
        return field

    def collect_processes(self):
        """
        Recursively descend the Field's Aggregators to create a list of all
        processes defined for this field. Includes Field's builtin processes.

        :return: (list of instances of Process subclasses) the processes
           defined for this field
        """

        def _collect(process_list, obj):
            for child in obj.children():
                if isinstance(child, Process):
                    process_list.append(child)
                else:
                    _collect(process_list, child)

        processes = (
            self.builtin_procs.copy()
        )  # copy since we're appending to this list recursively
        _collect(processes, self)
        return processes

    def save_process_data(self, **kwargs):
        """
        Allows a Process to store arbitrary data in the field's `process_data` dictionary
        for access by other processes.

        :param name: (str) the name of the data element (the dictionary key)
        :param value: (any) the value to store in the dictionary
        :return: none
        """
        for name, value in kwargs.items():
            self.process_data[name] = value

    def get_process_data(self, name, raiseError=None):
        """
        Retrieve a stored value from the field's `process_data` dictionary.

        :param name: (str) the name of the data element (the dictionary key)
        :return: (any) the value
        :raises OpgeeException: if the name is not found in `process_data`.
        """
        try:
            return self.process_data[name]
        except KeyError:
            if raiseError:
                raise OpgeeException(f"Process data dictionary does not include {name}")
            else:
                return None

    def resolve_process_choices(self, process_choice_dict=None):
        """
        Disable all processes referenced in a `ProcessChoice`, then enable only the processes
        in the selected `ProcessGroup`. The name of each `ProcessChoice` must also identify a
        field-level attribute, whose value indicates the user's choice of `ProcessGroup`.

        :param process_choice_dict: (dict) optional dictionary for nested process choices. Used
            in recursive calls only.
        :return: None
        """
        attr_dict = self.attr_dict

        if process_choice_dict is None:  # might be an empty dict, but that's ok
            process_choice_dict = self.process_choice_dict

        #
        # Turn off all processes identified in groups, then turn on those in the selected groups.
        #
        to_enable = []
        for choice_name, choice in process_choice_dict.items():
            attr = attr_dict.get(choice_name)
            if attr is None:
                raise OpgeeException(
                    f"ProcessChoice '{choice_name}' has no corresponding attribute in field '{self.name}'"
                )

            selected_group_name = attr.str_value().lower()

            for group_name, group in choice.groups_dict.items():
                procs, streams = group.processes_and_streams(self)

                if (
                        group_name == selected_group_name
                ):  # remember the ones to turn back on
                    to_enable.extend(procs)
                    to_enable.extend(streams)

                    # Handle nested process groups in the enabled group
                    self.resolve_process_choices(
                        process_choice_dict=group.process_choice_dict
                    )

                # disable all objects in all groups
                for obj in procs + streams:
                    obj.set_enabled(False)

        # enable the chosen procs and streams
        for obj in to_enable:
            obj.set_enabled(True)

    def sum_process_energy(self, processes_to_exclude=None) -> Energy:

        total = Energy()
        processes_to_exclude = processes_to_exclude or []
        for proc in self.processes():
            if proc.name not in processes_to_exclude:
                total.add_rates_from(proc.energy)

        return total

    def dump(self):
        """
        Print out a representation of the field's processes and streams for debugging.

        :return: none
        """
        visited = {}  # traverse a process only the first time it's encountered

        def debug(msg):
            print(msg)

        def visit(process):
            visited[process] = True
            next = []

            debug(f"\n> {process} outputs:")
            for stream in process.outputs:
                debug(f"  * {stream}")
                dst = stream.dst_proc
                if not dst in visited:
                    next.append(dst)

            for proc in next:
                visit(proc)

        debug(f"\n{self}:")
        visit(self.reservoir)

    def instances_by_class(self, cls):
        """
        Find one or more instances of ``cls`` known to this Field instance.
        If ``cls`` is ``Field``, just return ``self``; if ``cls`` is a subclass
        of ``Process``, find any instances in the field's ``process_dict``.

        :param cls: (Class) the class to find
        :return: (Field or list of instances of the Process subclass) if found,
          else None
        """
        if issubclass(cls, self.__class__):
            return self

        if issubclass(cls, Process):
            results = [proc for proc in self.processes() if isinstance(proc, cls)]
            return results or None

        return None

    #
    # Smart Defaults and Distributions
    #

    @SmartDefault.register("WOR", ["steam_flooding", "age", "SOR"])
    def WOR_default(self, steam_flooding, age, SOR):
        from math import exp

        # =IF(Steam_flooding_01=0,
        #     IF(4.021*EXP(0.024*Field_age)-4.021<=100, 4.021*EXP(0.024*Field_age)-4.021, 100),
        #     SOR)
        if steam_flooding:
            return SOR

        tmp = 4.021 * exp(0.024 * age.m) - 4.021
        return tmp if tmp <= 100 else 100

    @SmartDefault.register("SOR", ["steam_flooding"])
    def SOR_default(self, steam_flooding):
        return 3.0 if steam_flooding else 1.0

    # NOTE: If GOR is not known, it can be computed from API_grav, but we avoid
    # registering the dependency as this would create a dependency cycle.
    @SmartDefault.register("GOR", ["API"])
    def GOR_default(self, API):
        # =IF(API_grav<20,1122.4,IF(AND(API_grav>=20,API_grav<=30),1205.4,2429.3))
        if API.m < 20:
            return 1122.4
        elif 20 <= API.m <= 30:
            return 1205.4
        else:
            return 2429.3

    # TODO: handle special case of API depending on GOR
    # @SmartDefault.register('API', ['GOR'])
    # def api_default(self, GOR):
    #     # =IF(GOR > 10000, Z73, 32.8) [Z73 = constant 47]
    #     return 47.0 if GOR > 10000 else 32.8

    # TODO: Is the default always 7, or always the value of WOR plus 1?
    @SmartDefault.register("WIR", ["WOR"])
    def WIR_default(self, wor):
        # =J86+1  [J86 is WOR default, 6]
        return wor + 1

    @SmartDefault.register(
        "stabilizer_column", ["GOR", "gas_lifting", "oil_sands_mine"]
    )
    def stabilizer_default(self, GOR, gas_lifting, oil_sands_mine):
        # =IF(OR(J55+J56=1,AND(J85<=500,J52=0)),0,1)
        # J52 = gas_lifting (binary)
        # J55 = oil_sands_mine, integrated with upgrader (binary)
        # J56 = oil_sands_mine, non-integrated with upgrader (binary)
        # J85 = GOR
        #
        # Note: in OPGEEv4, there's one attribute 'oil_sands_mine' that can have values
        # 'None', 'Integrated with upgrader', or 'Non-integrated with upgrader'.
        return (
            0 if (oil_sands_mine != "None") or (not gas_lifting and GOR <= 500) else 1
        )

    # gas flooding injection ratio
    @SmartDefault.register("GFIR", ["flood_gas_type", "GOR"])
    def GFIR_default(self, flood_gas_type, GOR):
        # =IF(Flood_gas_type=1, 1.5*J85, IF(Flood_gas_type=2, 1200,  IF(Flood_gas_type=3, 10000,  1.5*J85)))
        # J85 is GOR
        if flood_gas_type == 1:
            return 1.5 * GOR

        elif flood_gas_type == 2:
            return 1200

        elif flood_gas_type == 3:
            return 10000

        else:
            return 1.5 * GOR

    @SmartDefault.register("depth", ["GOR"])
    def depth_default(self, GOR):
        # =IF(GOR > 10000, Z62, 7122), where Z62 has constant 8285 [gas field default depth]
        gas_field_default_depth = 8285.0
        return gas_field_default_depth if GOR.m > 1000 else 7122.0

    @SmartDefault.register("res_press", ["country", "depth", "steam_flooding"])
    def res_press_default(self, country, depth, steam_flooding):
        # =IF(AND('Active Field'!J59="California",'Active Field'!J54=1),100,0.5*(J62*0.43))
        # J59 = country, J62 = depth, J54 = steam_flooding
        return (
            100.0
            if (country == "California" and steam_flooding)
            else 0.5 * depth.m * 0.43
        )

    @SmartDefault.register("res_temp", ["depth"])
    def res_temp_default(self, depth):
        # = 70+1.8*J62/100 [J62 = depth]
        return 70 + 1.8 * depth.m / 100.0

    @SmartDefault.register("CrudeOilDewatering.heater_treater", ["API"])
    def heater_treater_default(self, API):
        # =IF(J73<18,1,0)  [J73 is API gravity]
        return API.m < 18

    @SmartDefault.register("num_prod_wells", ["oil_sands_mine", "oil_prod"])
    def num_producing_wells_default(self, oil_sands_mine, oil_prod):
        # =IF(OR(Oil_sands_mine_int_01=1,Oil_sands_mine_nonint_01=1),0,IF(ROUND(J63/87.5,0)<1,1,ROUNDUP(J63/87.5,0)))
        # J63 = oil_prod

        # Owing to constraint that requires num_prod_wells > 0, we return 1 for oils_sands mine.
        # num_prod_wells is used only in Exploration, ReservoirWellInterface, and DownholePump, which
        # shouldn't exist for oils sands mines.
        return 1 if oil_sands_mine != "None" else max(1.0, round(oil_prod.m / 87.5, 0))

    @SmartDefault.register(
        "num_water_inj_wells", ["oil_sands_mine", "oil_prod", "num_prod_wells"]
    )
    def oil_prod_default(self, oil_sands_mine, oil_prod, num_prod_wells):
        # =IF(OR(Oil_sands_mine_int_01=1,Oil_sands_mine_nonint_01=1),
        #     0,
        #     IF($J$63<=10,                     [J63 = oil_prod]
        #        ROUNDUP(J64*0.143,0),          [J64 = num_prod_wells]
        #        IF(AND($J$63>10,$J$63<=100),
        #           ROUNDUP(J64*0.267,0),
        #           IF(AND($J$63>100, $J$63<=1000),
        #              ROUNDUP(J64*0.512,0),
        #              ROUNDUP(J64*0.829,0)))))
        if oil_sands_mine != "None":
            return 0

        oil_prod_m = oil_prod.m

        if oil_prod_m <= 10:
            fraction = 0.143
        elif 10 < oil_prod_m <= 100:
            fraction = 0.267
        elif 100 < oil_prod_m <= 1000:
            fraction = 0.512
        else:
            fraction = 0.829

        return roundup(num_prod_wells * fraction, 0)

    @SmartDefault.register(
        "HeavyOilDilution.fraction_diluent", ["oil_sands_mine", "upgrader_type"]
    )
    def fraction_diluent_default(self, oil_sands_mine, upgrader_type):
        # =IF(AND(J56=1,J111=0),0.3,0) [J56 = 'oil sands mine nonint'; ; J111 = upgrader_type
        return (
            0.3
            if (oil_sands_mine == "Integrated with diluent" and upgrader_type == "None")
            else 0.0
        )

    @SmartDefault.register("fraction_elec_onsite", ["offshore"])
    def fraction_elec_onsite_default(self, offshore):
        return 1.0 if offshore else 0.0

    @SmartDefault.register(
        "fraction_remaining_gas_inj", ["natural_gas_reinjection", "gas_flooding"]
    )
    def fraction_remaining_gas_inj_default(self, natural_gas_reinjection, gas_flooding):
        # =IF(J53=1,1,IF(J50=1,0.5,0)) [J53 = gas_flooding, J50 = natural_gas_reinjection]
        return 1.0 if gas_flooding else (0.5 if natural_gas_reinjection else 0.0)

    @SmartDefault.register("ecosystem_richness", ["offshore"])
    def ecosystem_richness_default(self, offshore):
        # Excel has 3 separate booleans for low, med, high ecosystem richness, but we have
        # just one attribute here; value is one of ('Low carbon', 'Med carbon', 'High carbon').
        # Low : =IF(J70=1,1,0) [J70 = offshore]
        # Med : =IF(J70=1,0,1)
        # High: =IF(J70=1,0,0) # TODO: high carbon isn't used?
        return "Low carbon" if offshore else "Med carbon"

    @SmartDefault.register("field_development_intensity", ["offshore"])
    def field_development_intensity_default(self, offshore):
        # Excel has 3 separate booleans for low, med, high intensity, but we have
        # just one attribute here; value is one of ('Low', 'Med', 'High').
        # Low : =IF(J70=1,1,0) [J70 = offshore]
        # Med : =IF(J70=1,0,1)
        # High: =IF(J70=1,0,0) # TODO: high intensity isn't used?
        return "Low" if offshore else "Med"

    @SmartDefault.register("common_gas_process_choice", ["oil_sands_mine"])
    def common_gas_process_choice_default(self, oil_sands_mine):
        # Disable the ancillary group of gas-related processes when there is oil sand mine.
        # Otherwise enable all of those processes.
        return 'None' if oil_sands_mine != 'None' else 'All'

    @SmartDefault.register('prod_water_inlet_temp', ['country'])
    def prod_water_inlet_temp_default(self, country):

        temperature = 340 if country == 'Canada' else 140
        return ureg.Quantity(temperature, 'degF')

    @SmartDefault.register('num_gas_inj_wells', ['num_prod_wells'])
    def num_gas_inj_wells_default(self, num_prod_wells):
        return num_prod_wells * 0.25

    # TODO: decide how to handle "associated gas defaults", which is just global vs CA-LCFS values currently
