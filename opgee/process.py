'''
.. OPGEE process support

.. Copyright (c) 2021 Richard Plevin and Adam Brandt
   See the https://opensource.org/licenses/MIT for license details.
'''
from . import ureg
from .attributes import AttrDefs, AttributeMixin
from .core import XmlInstantiable, elt_name, instantiate_subelts, magnitude
from .container import Container
from .error import OpgeeException, AbstractMethodError, OpgeeStopIteration
from .emissions import Emissions
from .energy import Energy
from .log import getLogger
from .stream import Stream
from .utils import getBooleanXML

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
    d = {cls.__name__: cls for cls in get_subclasses(superclass)}
    return d


#
# Cache of known subclasses of Aggregator and Process
#
_Subclass_dict = None


def reload_subclass_dict():
    global _Subclass_dict

    _Subclass_dict = {
        Aggregator: _subclass_dict(Aggregator),
        Process: _subclass_dict(Process)
    }


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


class Process(XmlInstantiable, AttributeMixin):
    """
    The "leaf" node in the container/process hierarchy. Process is an abstract superclass: actual runnable Process
    instances must be of subclasses of Process, defined either in `opgee/processes/*.py` or in the user's files,
    provided in the configuration file in the variable ``OPGEE.ClassPath``.

    Each Process subclass must implement the ``run`` and ``bypass`` methods, described below.

    If a model contains process loops (cycles), one or more of the processes can call the method
    ``set_iteration_value()`` to store the value of a designated variable that is checked on each call to see if the
    change from the prior iteration is <= the value of Model attribute "maximum_change". If so,
    an ``OpgeeStopIteration`` exception is raised to terminate the run. In addition, a "visit" counter in each
    `Process` is incremented each time the process is run (or bypassed) and if the count >= the Model's
    "maximum_iterations" attribute, ``OpgeeStopIteration`` is likewise raised. Whichever limit is reached first
    will cause iterations to stop. Between model runs, the method ``iteration_reset()`` is called for all processes
    to clear the visited counters and reset the iteration value to None.
    """

    def __init__(self, name, desc=None, consumes=None, produces=None, attr_dict=None, start=False):
        name = name or self.__class__.__name__
        super().__init__(name)

        self.attr_dict = attr_dict or {}
        self.attr_defs = AttrDefs.get_instance()

        self._model = None  # @property "model" caches model here after first lookup

        self.desc = desc or name
        self.start = getBooleanXML(start)

        self.produces = set(produces) if produces else {}
        self.consumes = set(consumes) if consumes else {}

        self.extend = False
        self.field = None  # the Field we're part of, set on first lookup

        self.inputs = []  # Stream instances, set in Field.connect_processes()
        self.outputs = []  # ditto

        self.visit_count = 0  # increment the Process has been run

        self.energy = Energy()
        self.emissions = Emissions()

        self.iteration_count = 0
        self.iteration_value = None

    # Optional for Process subclasses
    def _after_init(self):
        pass

    #
    # Pass-through convenience methods for energy and emissions
    #
    def add_emission_rate(self, gas, rate):
        """
        Add to the stored rate of emissions for a single gas.

        :param gas: (str) one of the defined emissions (values of Emissions.emissions)
        :param rate: (float) the increment in rate in the Process' flow units (e.g., mmbtu (LHV) of fuel burned)
        :return: none
        """
        self.emissions.add_rate(gas, rate)

    def add_emission_rates(self, **kwargs):
        """
        Add emissions to those already stored, for of one or more gases, given as
        keyword arguments, e.g., add_emission_rates(CO2=100, CH4=30, N2O=6).

        :param kwargs: (dict) the keyword arguments
        :return: none
        """
        self.emissions.add_rates(**kwargs)

    def get_emission_rates(self, analysis):
        """
        Return the emission rates and the calculated GHG value. Uses the current
        choice of GWP values in the Analysis containing this process.

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

    def get_energy_rates(self, analysis):
        """
        Return the energy consumption rates.
        """
        # TBD: deal with LHV vs HHV here?
        return self.energy.rates()

    #
    # end of pass through energy and emissions methods
    #

    def set_gas_fugitives(self, stream, name):
        """

        :param stream:
        :param name:
        :return:
        """
        gas_fugitives = self.field.find_stream(name)
        loss_rate = self.venting_fugitive_rate()
        gas_fugitives.add_flow_rates_from(stream)
        gas_fugitives.multiply_flow_rates(loss_rate)
        gas_fugitives.set_temperature_and_pressure(60, 14.7)

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

    def get_environment(self):
        field = self.get_field()
        return field.environment

    def get_reservoir(self):
        field = self.get_field()
        return field.reservoir

    def find_stream(self, name, raiseError=False):
        """
        Convenience function to find a named stream from a Process instance by calling
        find_stream() on the enclosing Field instance.

        :param name: (str) the name of the Stream to find
        :param raiseError: (bool) whether to raise an error if the Stream is not found.
        :return: (Stream or None) the requested stream, or None if not found and `raiseError` is False.
        :raises: OpgeeException if `name` is not found and `raiseError` is True
        """
        field = self.get_field()
        return field.find_stream(name, raiseError=raiseError)

    def find_input_streams(self, stream_type, combine=True, raiseError=True):
        """
        Find the input streams connected to an upstream Process that handles the indicated
        `stream_type`, e.g., 'crude oil', 'raw water' and so on.

        :param direction: (str) 'input' or 'output'
        :param stream_type: (str) the generic type of stream a process can handle.
        :param combine: (bool) whether to (thermodynamically) combine multiple Streams into a single one
        :param raiseError: (bool) whether to raise an error if no handlers of `stream_type` are found.
        :return: (Stream or list of Streams) if `combine` is True, a single, combined stream is returned,
           otherwise a list of Streams.
        :raises: OpgeeException if no processes handling `stream_type` are found and `raiseError` is True
        """
        streams = [stream for stream in self.inputs if stream.dst_proc.handles(stream_type)]
        if not streams:
            if raiseError:
                raise OpgeeException(f"{self}: no input streams connect to processes handling '{stream_type}'")
            else:
                return []

        return Stream.combine(streams) if combine else streams

    def handles(self, stream_type):
        return stream_type in self.consumes

    def find_output_streams(self, stream_type, combine=True, as_dict=False, raiseError=True):
        """
        Find the output streams connected to a downstream Process that handles the indicated
        `stream_type`, e.g., 'crude oil', 'raw water' and so on.

        :param as_dict:
        :param stream_type: (str) the generic type of stream a process can handle.
        :param combine: (bool) whether to (thermodynamically) combine multiple Streams into a single one
        :param raiseError: (bool) whether to raise an error if no handlers of `stream_type` are found.
        :return: (Stream, list or dict of Streams)
        :raises: OpgeeException if no processes handling `stream_type` are found and `raiseError` is True
        """
        if as_dict:
            combine = False

        streams = [stream for stream in self.outputs if stream.dst_proc.handles(stream_type)]
        if not streams and raiseError:
            raise OpgeeException(f"{self}: no output streams connect to processes handling '{stream_type}'")

        return Stream.combine(streams) if combine else (streams if not as_dict else
                                                        {s.name: s for s in streams})

    def find_output_stream(self, stream_type, raiseError=True):
        """
        Find the first output stream connected to a downstream Process that handles the indicated
        `stream_type`, e.g., 'crude oil', 'raw water' and so on.

        :param direction: (str) 'input' or 'output'
        :param stream_type: (str) the generic type of stream a process can handle.
        :param raiseError: (bool) whether to raise an error if no handlers of `stream_type` are found.
        :return: (Streams or None)
        :raises: OpgeeException if no processes handling `stream_type` are found and `raiseError` is True
        """
        streams = self.find_output_streams(stream_type, combine=False, raiseError=raiseError)
        return streams[0] if streams else None

    def add_output_stream(self, stream):
        self.outputs.append(stream)

    def add_input_stream(self, stream):
        self.inputs.append(stream)

    def set_extend(self, extend):
        self.extend = extend

    def predecessors(self):
        """
        Return a Process's immediate precedent Processes.

        :return: (list of Process) the Processes that are the sources of
           Streams connected to `process`.
        """
        procs = [stream.src_proc for stream in self.inputs]
        return procs

    def set_iteration_value(self, value):
        """
        Store the value of a variable used to determine when an iteration loop
        has stabilized. When set, if the absolute value of the percent change
        in the value is less than the model's `iteration_epsilon`, the run loop
        is terminated by throwing an OpgeeStopIteration exception.

        :param value: (float) the value of a designated 'change' variable
        :return: none
        :raises: OpgeeStopIteration if the percent change in `value` (versus
            the previously stored value) is less than the `iteration_epsilon`
            attribute for the model.
        """
        m = self.model

        # If previously zero, set to a small number to avoid division by zero
        prior_value = self.iteration_value

        if prior_value is not None:
            delta = magnitude(abs(value - prior_value))
            if delta <= m.maximum_change:
                raise OpgeeStopIteration(f"Change <= maximum_change ({m.maximum_change}) in {self}")

        self.iteration_value = value

    def iteration_reset(self):
        self.clear_visit_count()
        self.iteration_value = None

    def run(self, analysis):
        """
        This method implements the behavior required of the Process subclass, when
        the Process is enabled. **Subclasses of Process must implement this method.**

        :param analysis: (Analysis) the `Analysis` used to retrieve global settings
        :return: None
        """
        raise AbstractMethodError(type(self), 'Process.run_internal')

    def run_or_bypass(self, analysis):
        """
        If the Process is enabled, run the process, otherwise bypass it, i.e., copy
        input streams to output streams.

        :param analysis: (Analysis) the repository of analysis-specific settings
        :return: None
        """
        if self.enabled:
            self.run(analysis)
        else:
            self.bypass()

        m = self.model
        if self.visit() >= m.maximum_iterations:
            raise OpgeeStopIteration(f"Maximum iterations ({m.maximum_iterations}) reached in {self}")

    # TBD: Can we create a generic method for passing inputs to outputs when disabled?
    # TBD: If not, this will become an abstract method.
    def bypass(self):
        """
        This method is called if a `Process` is disabled, allowing it to pass data from
        all input streams to output streams, effectively bypassing the disabled element.

        :return: none
        """
        pass

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
        _logger.info(f"Running {type(self)} name='{self.name}'")

    def venting_fugitive_rate(self, trial=None):
        """
        Look up venting/fugitive rate for this process. For user-defined processes not listed
        in the venting_fugitives_by_process table, the Process subclass must implement this
        method to override to the lookup.

        :param trial: (int or None) if `trial` is None, the mean venting/fugitive rate is returned.
           If `trial` is not None, it must be an integer trial number in the table's index.
        :return: (float) the fraction of the output stream assumed to be lost to the environment,
           either for the indicated `trial`, or the mean of all trial values if `trial` is None.
        """
        mgr = self.model.table_mgr
        tbl_name = 'venting_fugitives_by_process'
        df = mgr.get_table(tbl_name)

        # Look up the process by name, but fall back to the classname if not found by name
        columns = df.columns
        name = self.name
        if name not in columns:
            classname = self.__class__.__name__
            if classname != name:
                if classname in columns:
                    name = classname
                else:
                    raise OpgeeException(f"Neither '{name}' nor '{classname}' was found in table '{tbl_name}'")
            else:
                raise OpgeeException(f"'Class {classname}' was not found in table '{tbl_name}'")

        value = df[name].mean() if trial is None else df.loc[name, trial]
        return value

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
        start = a.get('start')

        classname = a['class']  # required by XML schema
        subclass = _get_subclass(Process, classname)
        attr_dict = subclass.instantiate_attrs(elt)

        produces = [node.text for node in elt.findall('Produces')]
        consumes = [node.text for node in elt.findall('Consumes')]

        obj = subclass(name, desc=desc, attr_dict=attr_dict, produces=produces, consumes=consumes, start=start)

        obj.set_enabled(getBooleanXML(a.get('enabled', '1')))
        obj.set_extend(getBooleanXML(a.get('extend', '0')))

        return obj


class Reservoir(Process):
    """
    Reservoir represents natural resources such as oil and gas reservoirs, and water sources.
    Each Field object holds a single Reservoir instance.
    """

    def run(self, analysis):
        self.print_running_msg()


class Environment(Process):
    """
    Represents the environment, which in OPGEE is just a sink for emissions. The Environment
    has only inputs (no outputs) and can be the destination (but not source) of streams. This
    restriction might change if air-capture of CO2 were introduced into the model. Each Analysis
    object holds a single Environment instance.
    """

    def __init__(self):
        super().__init__('Environment', desc='The Environment')

    # TBD: decide whether emissions are in streams or in separate calls inside Processes

    def run(self, analysis):
        self.print_running_msg()

        emissions = self.emissions

        emissions.data[:] = 0

        for stream in self.inputs:
            emissions.add_from_stream(stream)

        emissions.GHG(analysis.gwp)  # compute and cache GWP in emissions instance

    def report(self, analysis):
        print(f"{self}: cumulative emissions to Environment:\n{self.emissions}")


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
        return obj
