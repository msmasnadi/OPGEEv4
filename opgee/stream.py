'''
.. OPGEE stream support

.. Copyright (c) 2021 Richard Plevin and Adam Brandt
   See the https://opensource.org/licenses/MIT for license details.
'''
import pandas as pd
import re
from .attributes import AttributeMixin
from .core import XmlInstantiable, elt_name
from .error import OpgeeException
from .log import getLogger
from .utils import coercible

_logger = getLogger(__name__)

# constants to use instead of strings
PHASE_SOLID = 'solid'
PHASE_LIQUID = 'liquid'
PHASE_GAS = 'gas'

# Compile the patterns at load time for better performance
_carbon_number_pattern = re.compile('^C(\d+)$')
_hydrocarbon_pattern   = re.compile('^(C\d+)H(\d+)$')

def is_carbon_number(name):
    return (re.match(_carbon_number_pattern, name) is not None)

def is_hydrocarbon(name):
    return (name == 'CH4' or re.match(_hydrocarbon_pattern, name) is not None)

def molecule_to_carbon(molecule):
    if molecule == "CH4":
        return "C1"

    m = re.match(_hydrocarbon_pattern, molecule)
    if m is None:
        raise OpgeeException(f"Expected hydrocarbon molecule name like CxHy, got {molecule}")

    c_name = m.group(1)
    return c_name


def carbon_to_molecule(c_name):
    if c_name == "C1":
        return "CH4"

    m = re.match(_carbon_number_pattern, c_name)
    if m is None:
        raise OpgeeException(f"Expected carbon number name like Cn, got {c_name}")

    carbons = int(m.group(1))
    hydrogens = 2 * carbons + 2
    molecule = f"{c_name}H{hydrogens}"
    return molecule


#
# Can streams have emissions (e.g., leakage) or is that attributed to a process?
#
class Stream(XmlInstantiable, AttributeMixin):
    """
    The `Stream` class represent the flow rates of single substances or mingled combinations of co-flowing substances
    in any of the three states of matter (solid, liquid, or gas). Streams and stream components are specified in mass
    flow rates (e.g., Mg per day). The default set of substances is defined by ``Stream.components`` but can be
    extended by the user to include other substances, by setting the configuration file variable
    `OPGEE.StreamComponents`.

    Streams are defined within the `<Field>` element and are stored in a `Field` instance. The `Field` class tracks
    all `Stream` instances in a dictionary keyed by `Stream` name.
    """
    _phases = [PHASE_SOLID, PHASE_LIQUID, PHASE_GAS]

    # HCs with 1-60 carbon atoms, i.e., C1, C2, ..., C60
    _hydrocarbons = [f'C{n + 1}' for n in range(60)]
    _solids = ['PC']  # petcoke
    _liquids = ['oil']
    # _hc_molecules = ['CH4', 'C2H6', 'C3H8', 'C4H10']
    _gases = ['N2', 'O2', 'CO2', 'H2O', 'H2', 'H2S', 'SO2', 'air']
    _other = ['Na+', 'Cl-', 'Si-']

    #: The stream components tracked by OPGEE. This list can be extended by calling ``Stream.extend_components(names)``,
    #: or more simply by defining configuration file variable ``OPGEE.StreamComponents``.
    components = _solids + _liquids + _gases + _other + _hydrocarbons

    # Remember extensions to avoid applying any redundantly.
    # Value is a dict keyed by set(added_component_names).
    _extensions = {}

    @classmethod
    def extend_components(cls, names):
        """
        Allows the user to extend the global `Component` list. This must be called before any streams
        are instantiated. This method is called automatically if the configuration file variable
        ``OPGEE.StreamComponents`` is not empty: set it to a comma-delimited list of component names
        and they will be added to ``Stream.components`` at startup.

        :param names: (iterable of str) the names of new stream components.
        :return: None
        :raises: OpgeeException if any of the names were previously defined stream components.
        """
        name_set = frozenset(names)  # frozenset so we can use as index into _extensions

        if name_set in cls._extensions:
            _logger.debug(f"Redundantly tried to extend components with {names}")
        else:
            cls._extensions[name_set] = True

        # ensure no duplicate names
        bad = name_set.intersection(set(cls._extensions))
        if bad:
            raise OpgeeException(f"extend_components: these proposed extensions are already defined: {bad}")

        _logger.info(f"Extended stream components to include {names}")

        cls.components.extend(names)

    @classmethod
    def create_component_matrix(cls):
        """
        Create a pandas DataFrame to hold the 3 phases of the known Components.

        :return: (pandas.DataFrame) Zero-filled stream DataFrame
        """
        return pd.DataFrame(data=0.0, index=cls.components, columns=cls._phases)

    def __init__(self, name, number=0, temperature=None, pressure=None, src_name=None, dst_name=None, comp_matrix=None):
        super().__init__(name)

        self.components = self.create_component_matrix() if comp_matrix is None else comp_matrix
        self.number = number
        self.temperature = temperature
        self.pressure = pressure
        self.src_name = src_name
        self.dst_name = dst_name

        self.src_proc = None        # set in Field.connect_processes()
        self.dst_proc = None

        self.has_exogenous_data = False

    def __str__(self):
        number_str = f" #{self.number}" if self.number else ''
        return f"<Stream '{self.name}'{number_str}>"

    def component_phases(self, name):
        """
        Return the flow rates for all phases of stream component `name`.

        :param name: (str) The name of a stream component
        :return: (pandas.Series) the flow rates for the three phases of component `name`
        """
        return self.components.loc[name]

    def flow_rate(self, name, phase):
        """
        Set the value of the stream component `name` for `phase` to `rate`.

        :param name: (str) the name of a stream component
        :param phase: (str) the name of a phase of matter ('gas', 'liquid' or 'solid')
        :return: (float) the flow rate for the given stream component
        """
        rate = self.components.loc[name, phase]
        return rate

    def set_flow_rate(self, name, phase, rate):
        """
        Set the value of the stream component `name` for `phase` to `rate`.

        :param name: (str) the name of a stream component
        :param phase: (str) the name of a phase of matter ('gas', 'liquid' or 'solid')
        :param rate: (float) the flow rate for the given stream component
        :return: None
        """
        self.components.loc[name, phase] = rate

    #
    # Convenience functions
    #
    def gas_flow_rate(self, name):
        """Calls ``self.flow_rate(name, PHASE_GAS)``"""
        return self.flow_rate(name, PHASE_GAS)

    def liquid_flow_rate(self, name):
        """Calls ``self.flow_rate(name, PHASE_LIQUID)``"""
        return self.flow_rate(name, PHASE_LIQUID)

    def solid_flow_rate(self, name):
        """Calls ``self.flow_rate(name, PHASE_SOLID)``"""
        return self.flow_rate(name, PHASE_SOLID)

    def set_gas_flow_rate(self, name, rate):
        """Calls ``self.set_flow_rate(name, PHASE_GAS, rate)``"""
        return self.set_flow_rate(name, PHASE_GAS, rate)

    def set_liquid_flow_rate(self, name, rate):
        """Calls ``self.set_flow_rate(name, PHASE_LIQUID, rate)``"""
        return self.set_flow_rate(name, PHASE_LIQUID, rate)

    def set_solid_flow_rate(self, name, rate):
        """Calls ``self.set_flow_rate(name, PHASE_SOLID, rate)``"""
        return self.set_flow_rate(name, PHASE_SOLID, rate)

    def set_temperature_and_pressure(self, t, p):
        self.temperature = t
        self.pressure = p

    @classmethod
    def combine(cls, streams):
        """
        Thermodynamically combine multiple streams' components into a new
        anonymous Stream. This is used on input streams since it makes no
        sense for output streams.

        :param streams: (list of Streams) the Streams to combine
        :return: (Stream) if len(streams) > 1, returns a new Stream. If
           len(streams) == 1, the original stream is returned.
        """
        from statistics import mean

        if len(streams) == 1:   # corner case
            return streams[0]

        matrices = [stream.components for stream in streams]

        # TBD: for now, we naively sum the components, and average the temp and pressure
        comp_matrix = sum(matrices)
        temperature = mean([stream.temperature for stream in streams])
        pressure    = mean([stream.pressure for stream in streams])
        stream = Stream('-', temperature=temperature, pressure=pressure, comp_matrix=comp_matrix)
        return stream

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Stream> element
        :return: (Stream) instance of class Stream
        """
        a = elt.attrib
        src  = a['src']
        dst  = a['dst']
        name = a.get('name') or f"{src} => {dst}"

        # The following are optional
        number_str = a.get('number')
        number = coercible(number_str, int, raiseError=False) if number_str else None

        # There should be 2 attributes: temperature and pressure
        attr_dict = cls.instantiate_attrs(elt)
        expected = {'temperature', 'pressure'}
        if set(attr_dict.keys()) != expected:
            raise OpgeeException(f"Stream {name}: expected 2 attributes, {expected}")

        temp = attr_dict['temperature'].value
        pres = attr_dict['pressure'].value

        obj = Stream(name, number=number, temperature=temp, pressure=pres, src_name=src, dst_name=dst)
        comp_df = obj.components # this is an empty DataFrame; it is filled in below or at runtime

        # Set up the stream component info
        comp_elts = elt.findall('Component')
        obj.has_exogenous_data = len(comp_elts) > 0

        for comp_elt in comp_elts:
            a = comp_elt.attrib
            comp_name = elt_name(comp_elt)
            rate  = coercible(comp_elt.text, float)
            phase = a['phase']  # required by XML schema to be one of the 3 legal values
            unit  = a['unit']   # required by XML schema (TBD: use this)

            # convert hydrocarbon molecule name to carbon number format
            if is_hydrocarbon(comp_name):
                comp_name = molecule_to_carbon(comp_name)

            if comp_name not in comp_df.index:
                raise OpgeeException(f"Unrecognized stream component name '{comp_name}'.")

            # TBD: integrate units via pint and pint_pandas
            comp_df.loc[comp_name, phase] = rate

        return obj

# Deprecated? May be useful for Environment. Or not.
# class SignalingStream(Stream):
#     """
#     Augments Stream to have a dirty bit and a read method that returns a copy of the
#     stream contents and resets the stream to zeros, clearing the dirty bit. The main
#     use is for the Environment() process to collect emissions from all Processes, but
#     incrementally after each upstream process runs.
#     """
#     def __init__(self, name, number=0, temperature=None, pressure=None,
#                  src_name=None, dst_name=None, comp_matrix=None):
#
#         super().init(name, number=number, temperature=temperature, pressure=pressure,
#                      src_name=src_name, dst_name=dst_name, comp_matrix=comp_matrix)
#
#         self.dirty = False
#
#     def get_data(self):
#         if not self.dirty:
#             return None
#
#         comps = self.components
#         copy = comps.copy()
#         comps.loc[:, :] = 0.0
#         self.dirty = False
#
#         return copy
#
#     def set_flow_rate(self, name, phase, rate):
#         super().set_flow_rate(name, phase, rate)
#         self.dirty = True
