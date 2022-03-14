'''
.. OPGEE process support

.. Copyright (c) 2021 Richard Plevin and Adam Brandt
   See the https://opensource.org/licenses/MIT for license details.
'''
import pandas as pd
import pint
from typing import Union, Optional

from . import ureg
from .attributes import AttrDefs, AttributeMixin
from .config import getParamAsBoolean
from .core import OpgeeObject, XmlInstantiable, elt_name, instantiate_subelts, magnitude
from .container import Container
from .error import (OpgeeException, AbstractMethodError, OpgeeIterationConverged,
                    OpgeeMaxIterationsReached, ModelValidationError)
from .emissions import Emissions
from .energy import Energy
from .log import getLogger
from .stream import Stream
from .utils import getBooleanXML
from .drivers import get_efficiency
from .combine_streams import combine_streams
from .import_export import ImportExport

_logger = getLogger(__name__)


def get_subclasses(cls):
    for subclass in cls.__subclasses__():
        yield from get_subclasses(subclass)
        yield subclass


def _subclass_dict(superclass):
    """
    Return a dictionary of all defined subclasses of `superclass`, keyed by name.
    Does not descent beyond immediate subclasses.

    :return: (dict) subclasses keyed by name
    """
    allow_redef = getParamAsBoolean('OPGEE.AllowProcessRedefinition')

    d = {}

    for cls in get_subclasses(superclass):
        name = cls.__name__
        prior = d.get(name)

        if prior is None:
            d[name] = cls
        else:
            if prior != cls:
                msg = f"Class '{name}' is defined by both {cls} and {prior}"
                if allow_redef:
                    print(msg)
                else:
                    raise OpgeeException(msg)

    return d


#
# Cache of known subclasses of Aggregator and Process
#
_Subclass_dict: Optional[dict] = None


def _get_subclass(cls, subclass_name, reload=False):
    """
    Return the class for `subclass_name`, which must be a known subclass of `cls`.

    :param cls: (type) the class (Process or Aggregator) for which we're finding a subclass.
    :param subclass_name: (str) the name of the subclass
    :param reload: (bool) if True, reload the cache of subclasses of `cls`.
    :return: (type) the class object
    :raises: OpgeeException if `cls` is not Process or Aggregator or if the subclass is not known.
    """
    global _Subclass_dict

    if reload or _Subclass_dict is None:
        reload_subclass_dict()

    subclasses = _Subclass_dict.keys()
    if cls not in subclasses:
        raise OpgeeException(f"lookup_subclass: cls {cls} must be one of {list(subclasses)}")

    d = _Subclass_dict[cls]
    try:
        return d[subclass_name]
    except KeyError:
        raise OpgeeException(f"Class {subclass_name} is not a known subclass of {cls}")


class IntermediateValues(OpgeeObject):
    """
    Stores "interesting" intermediate values from processes for display in GUI.
    """

    def __init__(self):
        self.data = pd.DataFrame(columns=('value', 'unit', 'desc'))

    def store(self, name, value, unit=None, desc=None):
        # Strip magnitude and unit from Quantity objects
        if isinstance(value, pint.Quantity):
            unit = str(value.u)
            value = value.m

        self.data.loc[name, ('value', 'unit', 'desc')] = (value, unit or '', desc or '')

    def get(self, name):
        """
        Return the record associated with `name`.

        :param name: (str) the name of an intermediate value
        :return: (pd.Series) the row in the DataFrame of intermediate values for this process.
        """
        try:
            return self.data.loc[name]
        except KeyError:
            raise OpgeeException(f"An intermediate value for '{name}' was not found")


def run_corr_eqns(x1, x2, x3, x4, x5, coef_df):
    """

    :param x1:
    :param x2:
    :param x3:
    :param x4:
    :param x5:
    :param coef_df: Pandas.Dataframe
    :return: Pandas Series
    """

    x = pd.Series(
        data=[1, x1, x2, x3, x4, x5, x1 * x2, x1 * x3, x1 * x4, x1 * x5, x2 * x3, x2 * x4, x2 * x5, x3 * x4,
              x3 * x5, x4 * x5, x1 ** 2, x2 ** 2, x3 ** 2, x4 ** 2, x5 ** 2], index=coef_df.index)
    df = coef_df.mul(x, axis=0)
    result = df.sum(axis="rows")
    return result


class Process(XmlInstantiable, AttributeMixin):
    """
    The "leaf" node in the container/process hierarchy. ``Process`` is an abstract superclass: actual runnable Process
    instances must be of subclasses of ``Process``, defined either in `opgee/processes/*.py` or in the user's files,
    provided in the configuration file in the variable ``OPGEE.ClassPath``.

    Each Process subclass must implement the ``run`` and ``bypass`` methods, described below.

    If a model contains process loops (cycles), one or more of the processes can call the method
    ``set_iteration_value()`` to store the value(s) of a designated variable(s) to be checked on each call to see
    if the change from the prior iteration is <= the value of Model attribute "maximum_change". If so,
    an ``OpgeeIterationConverged`` exception is raised to terminate the run.

    In addition to testing for convergence, a "visit" counter in each ``Process`` is incremented each time the process
    is run (or bypassed) and if the count >= the Model's "maximum_iterations" attribute, ``OpgeeMaxIterationsReached``
    is likewise raised. Whichever limit is reached first will cause iterations to stop. Between model runs, the method
    ``field.reset()`` is called for all processes to clear the visited counters and reset the iteration value to None.

    See also :doc:`OPGEE XML documentation <opgee-xml>`
    """

    # Constants to support stream "finding" methods
    INPUT = 'input'
    OUTPUT = 'output'

    # the processes that have set iteration values
    iterating_processes = []

    def __init__(self, name, desc=None, attr_dict=None, cycle_start=False, impute_start=False,
                 boundary=None):
        name = name or self.__class__.__name__
        super().__init__(name)

        self.attr_dict = attr_dict or {}
        self.attr_defs = AttrDefs.get_instance()

        self.boundary = boundary    # the name of the boundary this Process defines, or None

        self._model = None  # @property "model" caches model here after first lookup

        self.desc = desc or name
        self.impute_start = getBooleanXML(impute_start)
        self.cycle_start = getBooleanXML(cycle_start)

        self.run_after = False  # whether to run this process after normal processing completes

        self.extend = False
        self.field = None  # the Field we're part of, set on first lookup

        self.inputs = []  # Stream instances, set in Field.connect_processes()
        self.outputs = []  # ditto

        self.visit_count = 0  # increment the Process has been run

        self.energy = Energy()
        self.emissions = Emissions()
        self.import_export = ImportExport()

        self.intermediate_results = None

        self.iv = IntermediateValues()

        # Support for stream validation. Subclasses can set these ivars
        # or redefine the methods required_inputs() / required_outputs()
        self._required_inputs = []
        self._required_outputs = []

        # Support for cycles
        self.iteration_count = 0
        self.iteration_value = None
        self.iteration_converged = False
        self.iteration_registered = False

        self.process_EF = None

    # Optional for Process subclasses
    def _after_init(self):
        self.check_attr_constraints(self.attr_dict)
        self.validate_streams()
        self.process_EF = self.get_process_EF()
        self.field = self.get_field()

    # TODO: stream validation and documentation
    def required_inputs(self):
        return self._required_inputs

    def required_outputs(self):
        return self._required_outputs

    def validate_streams(self):
        """
        Verify that each Process is connected to all required input and output streams.

        :return: none
        :raises ModelValidationError: if any required input or output streams are missing.
        """
        msgs = []

        for contents in self.required_inputs():
            if not self.find_input_stream(contents, as_list=True):
                msgs.append(f"{self} is missing an input stream containing '{contents}'")

        for contents in self.required_outputs():
            if not self.find_output_stream(contents, as_list=True):
                msgs.append(f"{self} is missing an output stream containing '{contents}'")

        if msgs:
            msg = '\n'.msgs
            raise ModelValidationError(msg)

    def reset(self):
        self.energy.reset()
        self.emissions.reset()
        self.reset_iteration()

    def set_run_after(self, value):
        self.run_after = value

    def within_boundary(self):
        """
        If `self` is a boundary Process, return the list of processes upstream of the boundary.
        The boundary Process must not be in a cycle.
        """
        if self.boundary is None:
            raise OpgeeException(f"within_boundary: '{self}' is not a boundary process].")

        visited = dict()

        def _visit(proc):
            if proc is None or visited.get(id(proc), False):
                return

            visited[id(proc)] = proc

            for p in proc.predecessors():
                _visit(p)

        _visit(self)
        return set(visited)

    def beyond_boundary(self):
        """
        If `self` is a boundary Process, return the list of processes beyond the boundary.
        The boundary Process must not be in a cycle.
        """
        if self.boundary is None:
            raise OpgeeException(f"beyond_boundary: '{self}' is not a boundary process.")

        visited = dict()

        def _visit(proc):
            if proc is None or visited.get(id(proc), False):
                return

            visited[id(proc)] = proc

            for p in proc.successors():
                _visit(p)

        _visit(self)
        return set(visited)


    #
    # Pass-through convenience methods for energy and emissions
    #
    def add_emission_rate(self, category, gas, rate):
        """
        Add to the stored rate of emissions for a single gas.

        :param category: (str) one of the defined emissions categories
        :param gas: (str) one of the defined emissions (values of Emissions.emissions)
        :param rate: (float) the increment in rate in the Process' flow units (e.g., mmbtu (LHV) of fuel burned)
        :return: none
        """
        self.emissions.add_rate(category, gas, rate)

    def add_emission_rates(self, category, **kwargs):
        """
        Add emissions to those already stored, for of one or more gases, given as
        keyword arguments, e.g., add_emission_rates(CO2=100, CH4=30, N2O=6).

        :param category: (str) one of the defined emissions categories
        :param kwargs: (dict) the keyword arguments
        :return: none
        """
        self.emissions.add_rates(category, **kwargs)

    def get_emission_rates(self, analysis, procs_to_exclude=None):
        """
        Return the emission rates and the calculated GHG value. Uses the current
        choice of GWP values in the Analysis containing this process.

        :param procs_to_exclude: ignored here, but provided for API consistency with
            Container class method of same name
        :return: ((pandas.Series, float)) a tuple containing the emissions Series
            and the GHG value computed using the model's current GWP settings.
        """
        return self.emissions.rates(gwp=analysis.gwp)

    def add_energy_rate(self, carrier, rate):
        """
        Set the rate of energy use for a single carrier.

        :param carrier: (str) one of the defined energy carriers (values of Energy.carriers)
        :param rate: (float) the rate of use (e.g., mmbtu/day (LHV) for all but electricity,
            which is in units of kWh/day.
        :return: none
        """
        self.energy.add_rate(carrier, rate)

    def add_energy_rates(self, dictionary):
        """
        Add to the energy use rate for one or more carriers.

        :param dictionary: (dict) the carriers and rates
        :return: none
        """
        self.energy.add_rates(dictionary)

    def get_energy_rates(self):
        """
        Return the energy consumption rates.
        """
        return self.energy.rates()

    def get_net_imported_product(self):
        """
        Return the net imported product energy rate (water is mass rate)
        :return:
        """
        imp_exp = self.import_export.imports_exports()
        return imp_exp[ImportExport.NET_IMPORTS]

    def set_import_from_energy(self, energy_use):
        imp_exp = self.field.import_export
        imp_exp.set_import_from_energy(self.name, energy_use)

    #
    # end of pass through energy and emissions methods
    #

    def set_gas_fugitives(self, stream, loss_rate) -> Stream:
        # TODO: complete this using Jeff's code
        """
        initialize the gas fugitives stream, get loss rate, copy..

        :param loss_rate:
        :param stream:
        :return:
        """
        gas_fugitives = Stream("gas fugitives", tp=self.field.stp)
        gas_fugitives.copy_gas_rates_from(stream)
        gas_fugitives.multiply_flow_rates(loss_rate)

        return gas_fugitives

    @property
    def model(self):
        """
        Return the `Model` this `Process` belongs to.

        :return: (Model) the enclosing `Model` instance.
        """
        if not self._model:
            self._model = self.find_parent('Model')

        return self._model

    def get_field(self):
        """
        Find and cache the Field instance that contains this Process

        :return: (Field) the enclosing Field instance
        """
        if not self.field:
            self.field = self.find_parent('Field')

        return self.field

    def visit(self):
        self.visit_count += 1
        return self.visit_count

    def visited(self):
        return self.visit_count

    def clear_visit_count(self):
        self.visit_count = 0

    def get_reservoir(self):
        return self.field.reservoir

    def find_stream(self, name, raiseError=False) -> Stream:
        """
        Convenience function to find a named stream from a Process instance by calling
        find_stream() on the enclosing Field instance.

        :param name: (str) the name of the Stream to find
        :param raiseError: (bool) whether to raise an error if the Stream is not found.
        :return: (Stream or None) the requested stream, or None if not found and `raiseError` is False.
        :raises: OpgeeException if `name` is not found and `raiseError` is True
        """
        return self.field.find_stream(name, raiseError=raiseError)

    def _find_streams_by_type(self, direction, stream_type, combine=False, as_list=False, raiseError=True) -> Union[
        Stream, list, dict]:
        """
        Find the input or output streams (indicated by `direction`) that contain the indicated
        `stream_type`, e.g., 'crude oil', 'raw water' and so on.

        :param direction: (str) 'input' or 'output'
        :param stream_type: (str) the generic type of stream a process can handle.
        :param combine: (bool) whether to (thermodynamically) combine multiple Streams into a single one
        :param as_list: (bool) return results as a list rather than as a dict
        :param raiseError: (bool) whether to raise an error if no handlers of `stream_type` are found.
        :return: (Stream, list or dict of Streams) depends on various keyword args
        :raises: OpgeeException if no processes handling `stream_type` are found and `raiseError` is True
        """
        if combine and as_list:
            raise OpgeeException(f"_find_streams_by_type: both 'combine' and 'as_list' cannot be True")

        assert direction in {self.INPUT, self.OUTPUT}
        stream_list = self.inputs if direction == self.INPUT else self.outputs
        streams = [stream for stream in stream_list if stream.enabled and stream.contains(stream_type)]

        if not streams and raiseError:
            raise OpgeeException(f"{self}: no {direction} streams contain '{stream_type}'")

        return combine_streams(streams, self.field.oil.API) if combine else (
            streams if as_list else {s.name: s for s in streams})

    def find_input_streams(self, stream_type, combine=False, as_list=False, raiseError=True) -> Union[
        Stream, list, dict]:
        """
        Convenience method to call `_find_streams_by_type` with direction "input"

        :param stream_type: (str) the generic type of stream a process can handle.
        :param combine: (bool) whether to (thermodynamically) combine multiple Streams into a single one
        :param as_list: (bool) return results as a list rather than as a dict
        :param raiseError: (bool) whether to raise an error if no handlers of `stream_type` are found.
        :return: (Stream, list or dict of Streams) depends on various keyword args
        :raises: OpgeeException if no processes handling `stream_type` are found and `raiseError` is True
        """
        return self._find_streams_by_type(self.INPUT, stream_type, combine=combine, as_list=as_list,
                                          raiseError=raiseError)

    def find_output_streams(self, stream_type, combine=False, as_list=False, raiseError=True) -> Union[
        Stream, list, dict]:
        """
        Convenience method to call `_find_streams_by_type` with direction "output"

        :param stream_type: (str) the generic type of stream a process can handle.
        :param combine: (bool) whether to (thermodynamically) combine multiple Streams into a single one
        :param as_list: (bool) return results as a list rather than as a dict
        :param raiseError: (bool) whether to raise an error if no handlers of `stream_type` are found.
        :return: (Stream, list or dict of Streams) depends on various keyword args
        :raises: OpgeeException if no processes handling `stream_type` are found and `raiseError` is True
        """
        return self._find_streams_by_type(self.OUTPUT, stream_type, combine=combine, as_list=as_list,
                                          raiseError=raiseError)

    def find_input_stream(self, stream_type, raiseError=True) -> Union[Stream, None]:
        """
        Find exactly one input stream connected to a downstream Process that produces the indicated
        `stream_type`, e.g., 'crude oil', 'raw water' and so on.

        :param stream_type: (str) the generic type of stream a process can handle.
        :param raiseError: (bool) whether to raise an error if no handlers of `stream_type` are found.
        :return: (Streams or None)
        :raises: OpgeeException if exactly one process producing `stream_type` is not found and `raiseError` is True
        """
        streams = self.find_input_streams(stream_type, as_list=True, raiseError=raiseError)
        if len(streams) != 1:
            if raiseError:
                raise OpgeeException(f"Expected one input stream with '{stream_type}'; found {len(streams)}")
            return None

        return streams[0]

    def find_output_stream(self, stream_type, raiseError=True) -> Union[Stream, None]:
        """
        Find exactly one output stream connected to a downstream Process that consumes the indicated
        `stream_type`, e.g., 'crude oil', 'raw water' and so on.

        :param stream_type: (str) the generic type of stream a process can handle.
        :param raiseError: (bool) whether to raise an error if no handlers of `stream_type` are found.
        :return: (Streams or None)
        :raises: OpgeeException if exactly one process consuming `stream_type` is not found and `raiseError` is True
        """
        streams = self.find_output_streams(stream_type, as_list=True, raiseError=raiseError)
        if len(streams) != 1:
            if raiseError:
                raise OpgeeException(f"Expected one output stream with '{stream_type}'; found {len(streams)}")
            return None

        stream = streams[0]
        if not stream.dst_proc.enabled:
            if raiseError:
                raise OpgeeException(f"'{stream}' is connected to a disabled process {stream.dst_proc}")
            return None

        return stream

    def add_output_stream(self, stream):
        self.outputs.append(stream)

    def add_input_stream(self, stream):
        self.inputs.append(stream)

    def set_extend(self, extend):
        self.extend = extend

    def predecessors(self) -> set:
        """
        Return a Process's immediate precedent Processes.

        :return: (set of Process) the Processes that are the sources of
           Streams connected to `process`.
        """
        procs = set([stream.src_proc for stream in self.inputs])
        return procs

    def successors(self) -> set:
        """
        Return a Process's immediately following Processes.

        :return: (set of Process) the Processes that are the destinations
           of Streams connected to `process`.
        """
        procs = set([stream.dst_proc for stream in self.outputs])
        return procs

    def set_iteration_value(self, value):
        """
        Store the value of one or more variables used to determine when an
        iteration loop has stabilized. When set, if the absolute value of the
        change in each value is less than the model's `maximum_change`, the
        run loop is terminated by throwing an OpgeeStopIteration exception.

        :param value: (float, list/tuple of floats, pandas.Series) the values of
            designated 'change' variables to compare each iteration. If a list, tuple,
            or Series is used, all values contained therein must be within `maximum_change`
            of the previously stored value.
        :return: none
        :raises: OpgeeIterationConverged if the change in `value` (versus the
            previously stored value) is less than the `maximum_change`
            attribute for the model. If a list/tuple/Series of floats is passed in
            `value`, all of the contained values must pass this test.
        """
        _logger.debug(f"{self.name}:count = {self.visit_count}")
        if self.iteration_converged:
            return  # nothing left to do

        m = self.model

        # register the process and remember its registration so we don't do it again
        if not self.iteration_registered:
            self.register_iterating_process(self)

        # If previously zero, set to a small number to avoid division by zero
        prior_value = self.iteration_value

        # helper function to check for convergence of each element of a tuple
        def converged(prior_value, value):
            delta = magnitude(abs(value - prior_value))
            is_converged = delta <= m.maximum_change
            if not is_converged:
                _logger.debug(f"process: {self.name}")
                _logger.debug(f"current value is {value}")
                _logger.debug(f"prior value is {prior_value}")
            return is_converged

        if prior_value is not None:
            if type(prior_value) != type(value):
                raise OpgeeException(f"Type of iterator value changed; was: {type(prior_value)} is: {type(value)}")

            # TODO: we expect the series to have no units
            if isinstance(value, pd.Series):
                diff = abs(value - prior_value)  # type: pd.Series
                if all(diff <= m.maximum_change):
                    self.iteration_converged = True
                    self.check_iterator_convergence()
                else:
                    _logger.debug(f"process: {self.name}")
                    _logger.debug(f"current value is {value}")
                    _logger.debug(f"prior value is {prior_value}")
            else:
                pairs = zip(prior_value, value) if isinstance(value, (tuple, list)) \
                    else [(prior_value, value)]  # make a list of the one pair

                if all([converged(old, new) for old, new in pairs]):
                    self.iteration_converged = True
                    # Raise OpgeeStopIteration exception if all process's
                    # iterator values have converged.
                    self.check_iterator_convergence()

        self.iteration_value = value

    @classmethod
    def register_iterating_process(cls, process):
        process.iteration_registered = True
        cls.iterating_processes.append(process)

    @classmethod
    def check_iterator_convergence(cls):
        """
        Check whether the current process is the last of all process iterator values to converge.
        stop when one converges but others have yet to do so.

        :return: none.
        :raises OpgeeIterationConverged: if all processes have converged.
        """
        if all([proc.iteration_converged for proc in cls.iterating_processes]):
            raise OpgeeIterationConverged(f"Change <= maximum_change in all iterating processes")

    @classmethod
    def reset_all_iteration(cls):
        """
        Reset the iteration value and counter in all iterating processes.

        :return: none
        """
        for proc in cls.iterating_processes:
            proc.reset_iteration()

    def reset_iteration(self):
        self.clear_visit_count()
        self.iteration_value = None
        self.iteration_converged = False
        self._reset_before_iteration()

    def _reset_before_iteration(self):
        """
        Optional method to allow iterating processes to reset any state before
        a new iteration cycle begins.

        :return: none
        """
        pass

    def run(self, analysis):
        """
        This method implements the behavior required of the Process subclass, when
        the Process is enabled. **Subclasses of Process must implement this method.**

        :param analysis: (Analysis) the `Analysis` used to retrieve global settings
        :return: None
        """
        raise AbstractMethodError(Process, 'Process.run')

    def check_balances(self):
        """

        :return:
        """
        pass

    def run_if_enabled(self, analysis):
        """
        If the Process is enabled, run the process, otherwise do nothing.

        :param analysis: (Analysis) the repository of analysis-specific settings
        :return: None
        """
        if self.enabled:
            self.run(analysis)

            m = self.model
            if self.visit() >= m.maximum_iterations:
                raise OpgeeMaxIterationsReached(f"Maximum iterations ({m.maximum_iterations}) reached in {self}")

    def impute(self):
        """
        Called for Process instances upstream of Stream with exogenous input data, allowing
        those nodes to impute their own inputs from the output Stream.

        :return: none
        """
        pass

    #
    # The next two methods are provided to allow Aggregator to call children() and
    # run_children() without type checking. For Processes, these are just no-ops.
    #
    def children(self):
        return []

    def run_children(self, **kwargs):
        pass

    def print_running_msg(self):
        _logger.debug(f"Running {type(self)} name='{self.name}'")

    def venting_fugitive_rate(self):
        return self.attr('leak_rate')

    @staticmethod
    def get_energy_consumption_stages(prime_mover_type, brake_horsepower_of_stages):
        energy_consumption_of_stages = []
        for brake_horsepower in brake_horsepower_of_stages:
            eff = get_efficiency(prime_mover_type, brake_horsepower)
            energy_consumption = (brake_horsepower * eff).to("mmBtu/day")
            energy_consumption_of_stages.append(energy_consumption)

        return energy_consumption_of_stages

    @staticmethod
    def get_energy_consumption(prime_mover_type, brake_horsepower):
        eff = get_efficiency(prime_mover_type, brake_horsepower)
        energy_consumption = (brake_horsepower * eff).to("mmBtu/day")

        return energy_consumption

    def init_intermediate_results(self, names):
        """

        :param names:
        :return:
        """
        self.intermediate_results = {name: (Energy(), Emissions()) for name in names}

    def get_intermediate_results(self):
        """
        This will be overridden in the water treatment subprocess

        :return: A dictionary of energy and emission instances or None
        """

        return self.intermediate_results

    def sum_intermediate_results(self):
        """
        Sum intermediate energy and emission results

        :return:
        """

        if self.intermediate_results is None:
            return

        self.energy.reset()
        self.emissions.reset()

        for key, (energy, emission) in self.intermediate_results.items():
            self.energy.add_rates_from(energy)
            self.emissions.add_rates_from(emission)

    def get_process_EF(self):
        """
        Look up emission factor for this process to calculate the combustion emission.
        For user-defined processes not listed in the process_EF table, the Process subclass must implement this
        method to override to the lookup.

        :return: (float) a pandas series of emission factor
           for natural gas, upgrader proc.gas, NGL, diesel, residual fuel, pet.coke
           (unit = gGHG/mmBtu)
        """
        process_EF_df = self.model.process_EF_df
        tbl_name = "process-specific-EF"

        # Look up the process by name, but fall back to the classname if not found by name
        name = self.name
        if name not in process_EF_df.index:
            classname = self.__class__.__name__
            if classname != name:
                if classname in process_EF_df.index:
                    name = classname
                else:
                    return None
                    # raise OpgeeException(f"Neither '{name}' nor '{classname}' was found in table '{tbl_name}'")
            else:
                return None
                # raise OpgeeException(f"'Class {classname}' was not found in table '{tbl_name}'")

        emission_series = pd.Series({fuel: process_EF_df.loc[name, fuel] for fuel in process_EF_df.columns},
                                    dtype="pint[g/mmBtu]")
        return emission_series

    def all_streams_ready(self, input_stream_contain):
        """
        Check if all the steams from enabled process are ready


        :param input_stream_contain: (str) name of input steam contains
        :return: boolean
        """
        input_streams = self.find_input_streams(input_stream_contain)
        for stream in input_streams.values():
            if stream.src_proc.enabled and stream.is_uninitialized():
                return False
        return True

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Process> element
        :return: (Process) instance populated from XML
        """
        name = elt_name(elt)
        a = elt.attrib
        desc = a.get('desc')
        impute_start = a.get('impute-start')
        cycle_start = a.get('cycle-start')
        boundary = a.get('boundary')  # optional

        classname = a['class']  # required by XML schema
        subclass = _get_subclass(Process, classname)
        attr_dict = subclass.instantiate_attrs(elt, is_process=True)

        obj = subclass(name, desc=desc, attr_dict=attr_dict,
                       cycle_start=cycle_start, impute_start=impute_start,
                       boundary=boundary)

        obj.set_enabled(a.get('enabled', '1'))
        obj.set_extend(a.get('extend', '0'))

        obj.set_run_after(getBooleanXML(a.get('after', '0')))

        return obj


class Reservoir(Process):
    """
    Reservoir represents natural resources such as oil and gas reservoirs, and water sources in the subsurface.
    Each Field object holds a single Reservoir instance.
    """

    def __init__(self, *args, **kwargs):
        super().__init__("Reservoir", desc='The Reservoir')

    def run(self, analysis):
        self.print_running_msg()

# class Before(Process):
#     def run(self, analysis):
#         pass
#
#     def impute(self):
#         pass

# class Environment(Process):
#     """
#     Represents the environment, which in OPGEE is just a sink for emissions. The Environment
#     has only inputs (no outputs) and can be the destination (but not source) of streams. This
#     restriction might change if air-capture of CO2 were introduced into the model. Each Analysis
#     object holds a single Environment instance.
#     """
#
#     def __init__(self, *args, **kwargs):
#         super().__init__('Environment', desc='The Environment')
#         self.set_run_after(True)
#
#     def run(self, analysis):
#         self.print_running_msg()
#
#         emissions = self.emissions
#         emissions.reset()
#
#         # TBD: unclear whether this is useful
#         for stream in self.inputs:
#             emissions.add_from_stream(EM_OTHER, stream)
#
#         emissions.compute_GHG(analysis.gwp)  # compute and cache GWP in emissions instance
#
#     def report(self, analysis):
#         print(f"{self}: cumulative emissions to Environment:\n{self.emissions}")


# TBD: move this to tests/utils_for_tests.py after removing references from opgee.xml
# Required to load opgee.xml and some test XML files
class After(Process):
    def run(self, analysis):
        pass

    def impute(self):
        pass


#
# This class is defined here rather than in container.py to avoid import loops and to
# allow the reference to Aggregator above.
#
class Aggregator(Container):
    def __init__(self, name, attr_dict=None, aggs=None, procs=None):
        super().__init__(name, attr_dict=attr_dict, aggs=aggs, procs=procs)

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Aggregator> element
        :return: (Aggregator) instance populated from XML
        """
        name = elt_name(elt)

        aggs = instantiate_subelts(elt, Aggregator)
        procs = instantiate_subelts(elt, Process)

        attr_dict = cls.instantiate_attrs(elt)

        obj = cls(name, attr_dict=attr_dict, aggs=aggs, procs=procs)

        # Aggregators are disabled if they are empty or contain only disabled aggs & procs
        enabled = not all([not child.is_enabled() for child in aggs + procs])
        obj.set_enabled(enabled)

        return obj


def reload_subclass_dict():
    global _Subclass_dict

    _Subclass_dict = {
        Aggregator: _subclass_dict(Aggregator),
        Process: _subclass_dict(Process)
    }
