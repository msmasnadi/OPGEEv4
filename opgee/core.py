'''
.. Core OPGEE objects

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
'''
from pint import UnitRegistry, Quantity
import sys
from .error import OpgeeException
from .log import getLogger
from .XMLFile import XMLFile
from .utils import coercible, resourceStream
from .stream_component import get_component_matrix, Phases

_logger = getLogger(__name__)

# Note that we probably will define some of our own units:
# From a file:
# ureg.load_definitions('/your/path/to/my_def.txt')
#
# Or one at a time:
# ureg.define('dog_year = 52 * day = dy')
Ureg = UnitRegistry()

# Other notes:
# "psi" is defined, but neither "psig" nor "psia" are defined. (N psia = N psig + 1 atmosphere)
# - Is PSIG used anywhere in the model? We might just define "psia = psi", "scf/bbl liquid"
Ureg.define('psia = psia')
Ureg.define('scf = ft**3')
Ureg.define("bbl_oil = 42 * gal = _ = bbl_steam = bbl_water = bbl_liquid")
Ureg.define("degAPI = dimensionless") # ratio of density of oil to density of water
Ureg.define("mol% = dimensionless")
Ureg.define("pct = dimensionless")
Ureg.define("gCO2eq = grams")

#
# TBD: Each class should also know how to emit its equivalent XML.
#

def class_from_str(classname, module_name=__name__):
    m = sys.modules[module_name]   # get the module object

    try:
        cls = getattr(m, classname)

        if not issubclass(cls, XmlInstantiable):
            raise OpgeeException(f'Class {classname} is not a subclass of XmlInstantiable')

        return cls

    except AttributeError:
        raise OpgeeException(f'Class {classname} is not a defined OPGEE class')

# Return a list of XmlInstantiable subclasses in a named module
def xml_instantiable_classes(module_name): # e.g., 'opgee.core'
    m = sys.modules[module_name]
    classes = [obj for (name, obj) in m.__dict__.items() if \
               isinstance(obj, type) and issubclass(obj, XmlInstantiable) \
               and name != 'XmlInstantiable']
    return classes

def subelt_value(elt, tag, coerce=None, with_unit=True, required=True):
    """
    Get the value from the text of the named subelement of `elt`. If `required`
    is True and the element is not found, raise an error. If not found and `required`
    is False, return None. Regardless of `required`, an error is raised if multiple
    subelements with `tag` are found.

    :param elt: (etree.Element) the parent element
    :param tag: (str) the tag of the subelement
    :param coerce (type) a type to coerce the value
    :param with_unit (bool) if True, return a Value instance with value and unit.
    :param required: (bool) whether to raise an error if element is not found,
       or if found and `with_unit` is True, there is no unit attribute.
    :return: (str) the value found in the subelement, converted by `coerce` if
       `coerce` is not None, or if `with_unit` is True, an instance of Value.
    :raises: OpgeeException if `required` is True and the subelement isn't found,
       or if multiple subelements with `tag` are found, or if a required element
       is missing a unit attribute and `with_unit` is True.
    """
    subs = elt.findall(tag)
    count = len(subs)
    if count == 0 and not required:
        return None

    if count != 1:
        raise OpgeeException(f"Expected one {tag} subelements below {elt}; found {count}")

    subelt = subs[0]
    value = subelt.text if coerce is None else coercible(subelt.text, coerce)
    unit = subelt.attrib.get('unit')

    if with_unit:
        if unit is None:
            raise OpgeeException(f"subelt_value: unit is missing from element {subelt}")
        return Quantity(value, Ureg[unit])
    else:
        return value

def elt_name(elt):
    return elt.attrib['name']

def instantiate_subelts(elt, tag, cls):
    objs = [cls.from_xml(e) for e in elt.findall(tag)]
    return objs

def superclass(cls):
    """
    Get the first superclass of the given class from the __mro__ (method resolution order).
    This is necessary since super().xml_attrs() did not work as required for class methods.

    :param cls: (class) The class to get the superclass of
    :return: (class) The first superclass in class's MRO, if any, else None
    """
    mro = cls.__mro__
    return mro[1] if len(mro) > 1 else None


# Top of hierarchy, because this is often useful...
class OpgeeObject():
    pass


class ClassAttributes(OpgeeObject):
    """
    Support for parsing attributes.xml
    """
    def __init__(self, elt):
        super().__init__()

        class_attr = elt.attrib.get('class')
        self.class_name = class_attr or elt.tag
        self.element_name = elt.tag

        self.group_dict = {}    # key is group name; value is list of attribute names in group
        self.option_dict = {}   # key is name of <Options> group; value is dict of opt_num : opt_desc
        self.attr_dict = {}     # key is attribute name; value is instance of class 'A'

        group_elts = elt.findall('Group')   # so far, only in Field elements, but this may change
        group_dict = self.group_dict
        attr_dict  = self.attr_dict
        option_dict = self.option_dict

        # add attributes to the attr_dict from a list of XML <A> elements
        def _add_attrs(a_elts):
            for elt in a_elts:
                attr_dict[elt_name(elt)] = A.from_xml(elt)

        # add attributes defined within <Group> elements
        for group_elt in group_elts:
            group_name = elt_name(group_elt)
            elts = group_elt.findall('A')
            _add_attrs(elts)
            group_dict[group_name] = [elt_name(e) for e in elts]

        # add top-level attributes
        elts = elt.findall('A')
        _add_attrs(elts)

        # add all <Option> elements beneath elt (may be within <Group> or not)
        options_elts = elt.xpath('.//Options')
        for options_elt in options_elts:
            opts_name = elt_name(options_elt)
            opt_elts = options_elt.findall('Option')
            option_dict[opts_name] = [(e.attrib['number'], e.text) for e in opt_elts]  # TBD: store number as int?


class Attributes(OpgeeObject):
    """
    Parse and provide access to attributes.xml metadata file.
    """
    def __init__(self):
        super().__init__()
        self.classes = None  # will be dict: key is class name: Field, Process's or Technology's class; value is ClassAttributes instance

        stream = resourceStream('etc/attributes.xml', stream_type='bytes', decode=None)
        attr_xml = XMLFile(stream, schemaPath='etc/attributes.xsd')
        root = attr_xml.tree.getroot()

        # user_attr_file = getParam("OPGEE.UserAttributesFile")
        # if user_attr_file:
        #     user_attr_xml = XMLFile(user_attr_file, schemaPath='etc/attributes.xsd')
        #     user_root = user_attr_xml.tree.getroot()
        #
        #     # TBD: merge user's definitions into standard ones

        class_attrs = [ClassAttributes(elt) for elt in root]
        d = {obj.class_name : obj for obj in class_attrs}
        self.classes = d


class XmlInstantiable(OpgeeObject):
    """
    This is the superclass for all classes that are instantiable from XML. The requirements of
    such classes are:
    1. They subclass from XmlInstantiable or its subclasses
    2. They define __init__(self, name, **kwargs) and call super().__init__(name)
    3. They define @classmethod from_xml(cls, element) to create an instance from XML.
    4. Subclasses of Technology also implement a run() method to perform the required operation.
    """
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.enabled = True

    @classmethod
    def from_xml(cls, elt):
        raise OpgeeException(f'Called abstract method XmlInstantiable.from_xml() -- {cls} is missing this required method.')

    def __str__(self):
        type_str = type(self).__name__
        return f'<{type_str} name="{self.name}">'

    def is_enabled(self):
        return self.enabled

    def set_enabled(self, value):
        self.enabled = value

# to avoid redundant reporting
_undefined_units = {}

# The <A> element
class A(XmlInstantiable):
    def __init__(self, name, value=None, atype=None, option_set=None, unit=None):
        super().__init__(name)

        if atype is not None:
            value = coercible(value, atype)

        if unit and unit not in _undefined_units:
            if unit not in Ureg:
                _logger.warn(f"Unit '{unit}' is not in the UnitRegistry")
                _undefined_units[unit] = 1
                unit = 'dimensionless'

        self.value = Quantity(value, Ureg[unit]) if unit else value

        self.option_set = option_set        # the name of the option set, if any
        self.unit = unit
        self.atype = atype

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing an <A> element
        :return: (A) instance of class A
        """
        a = elt.attrib

        if elt.text is None:
            from lxml import etree
            elt_xml = etree.tostring(elt).decode()
            raise OpgeeException(f"Empty <A> elements are not allowed: {elt_xml}")

        obj = A(a['name'], value=elt.text, atype=a.get('type'), unit=a.get('unit'),
                option_set=a.get('options'))

        return obj

#
# Can streams have emissions (e.g., leakage) or is that attributed to a process?
#
class Stream(XmlInstantiable):
    def __init__(self, name, number, temp=None, pressure=None, src=None, dst=None):
        super().__init__(name)

        self.number = number
        self.temperature = temp
        self.pressure = pressure
        self.src = src
        self.dst = dst
        self.comp_mat = get_component_matrix()

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Stream> element
        :return: (Stream) instance of class Stream
        """
        a = elt.attrib
        name   = a['name']
        number = a['number']

        temp = subelt_value(elt, 'Temperature', coerce=float)
        pres = subelt_value(elt, 'Pressure',    coerce=float)

        src = elt_name(elt.find('Source'))
        dst = elt_name(elt.find('Destination'))

        obj = Stream(name, number, temp=temp, pressure=pres, src=src, dst=dst)
        comp_mat = obj.comp_mat

        # Set the stream component info
        comp_elts = elt.findall('Component')
        for comp_elt in comp_elts:
            comp_name = elt_name(comp_elt)
            rate = subelt_value(elt, 'Rate', coerce=float)
            phase = subelt_value(elt, 'Phase', with_unit=False)

            if phase not in Phases:
                raise OpgeeException(f"Phase '{phase}' is not known. Must be one of {Phases}")

            comp_mat.set_component(comp_name, phase, rate)

        return obj


class Container(XmlInstantiable):
    """
    Generic hierarchical node element, has a name and contains subclasses of
    itself, recursively. Subclasses add attributes to those defined in superclass.
    """
    def __init__(self, name):
        super().__init__(name)
        self.children = []
        self.emissions = None       # TBD: Multiple Streams?

    def set_children(self, children):
        self.children = children

    # default is no-op
    def run(self, **kwargs):
        pass

    # Subclass should call this before or after local processing
    def run_children(self, **kwargs):
        if self.is_enabled():
            for child in self.children:
                child.run_children()    # depth first
                child.run(**kwargs)     # run self after running children

    def compute_ins_outs(self):
        """
        Method to compute inputs and outputs for this Container, which is
        computed as the inputs of child processes that are not bound to
        streams for all leaf process nodes. Something like that.

        :return: None
        """
        pass

    def aggregate_flows(self):
        """
        Compute total flows into and out of this container by summing those from
        the contained objects. Results are stored in the container. (Cached? Dynamic?)

        :return: None
        """
        pass


class Process(Container):
    def __init__(self, name):
        super().__init__(name)

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Process> element
        :return: (Process) instance populated from XML
        """
        name = elt_name(elt)
        classname = elt.attrib.get('class') or 'Process'    # TBD: allow use without class=""?

        procs = instantiate_subelts(elt, 'Process', Process)
        techs = instantiate_subelts(elt, 'Technology', Technology)

        # TBD: fill in Smart Defaults here, or assume they've been filled already?
        attrs = instantiate_subelts(elt, 'A', A)

        # TBD: lookup the classname (maybe it has to be class="pkg.classname" ?
        # process_subclass = lookup classname or Process
        obj = Process(name, procs=procs, techs=techs)
        return obj

    def run(self, **kwargs):
        """
        Run all sub-processes, passing variables, settings, and streams for the parent field.

        :param kwargs: (dict) keyword arguments
        :return:
        """
        pass


class Technology(Container):
    def __init__(self, name):
        super().__init__(name)

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Technology> element
        :return: (Technology) instance populated from XML
        """

        # TBD: fill in Smart Defaults here, or assume they've been filled already?
        attrs = instantiate_subelts(elt, 'A', A)

        # TBD: lookup the classname (maybe it has to be class="pkg.classname" ?
        # tech_subclass = lookup classname or Technology

        obj = Technology()
        return obj

    def run(self, **kwargs):
        """
        Run all sub-processes, passing variables, settings, and streams for the parent field.

        :param kwargs: (dict) keyword arguments
        :return:
        """
        pass


class Field(Container):

    def __init__(self, name, location=None, is_offshore=None, procs=None, techs=None):
        super().__init__(name)

        self.location = location  # store lat/long?
        self.streams  = None  # streams to or from the environment
        self.procs = procs
        self.techs = techs

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Field> element
        :return: (Field) instance populated from XML
        """
        name = elt_name(elt)

        location = subelt_value(elt, 'location')
        is_offshore = subelt_value(elt, 'is_offshore', coerce=int)

        procs = instantiate_subelts(elt, 'Process', Process)
        techs = instantiate_subelts(elt, 'Technology', Technology)

        # TBD: fill in Smart Defaults here, or assume they've been filled already?
        attrs = instantiate_subelts(elt, 'A', A)

        obj = Field(name, location=location, is_offshore=is_offshore, procs=procs, techs=techs)
        return obj

    def run(self, **kwargs):
        """
        Run all stages

        :param kwargs:
        :return:
        """
        pass


class Analysis(Container):
    def __init__(self, name, functional_unit=None, energy_basis=None,
                 variables=None, settings=None, streams=None, fields=None):
        super().__init__(name)

        # Global settings
        self.functional_unit = functional_unit
        self.energy_basis = energy_basis
        self.variables = variables   # dict of standard variables
        self.settings  = settings    # user-controlled settings
        self.streams   = streams     # define these here to avoid passing separately?
        self.fields    = fields

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Analysis> element
        :return: (Analysis) instance populated from XML
        """
        name = elt_name(elt)
        fn_unit  = subelt_value(elt, 'FunctionalUnit', with_unit=False)
        en_basis = subelt_value(elt, 'EnergyBasis', with_unit=False)
        fields = instantiate_subelts(elt, 'Field', Field)

        obj = Analysis(name, functional_unit=fn_unit, energy_basis=en_basis, fields=fields)
        return obj

    def run(self, **kwargs):
        """
        Run all fields, passing variables and settings.

        :param kwargs:
        :return:
        """
        pass


class Model(Container):
    # __attributes__ = [Attr('children', childTag='Analysis')]

    def __init__(self, name, analysis):
        super().__init__(name)
        self.analysis = analysis

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Model> element
        :return: (Model) instance populated from XML
        """
        analyses = instantiate_subelts(elt, 'Analysis', Analysis)
        count = len(analyses)
        if count != 1:
            raise OpgeeException(f"Expected on <Analysis> element; got {count}")

        obj = Model(elt_name(elt), analyses[0])
        return obj

# TBD: grab a path like OPGEE.UserClassPath, which defaults to OPGEE.ClassPath
# TBD: split these and load all *.py files in each directory (if a directory;
# TBD: allow specify specific files in path as well)
# TBD: import these into this module so they're found by class_from_str()?
# TBD: Alternatively, create dict of base classname and actual module it's in
# TBD: by looping over sys.modules[name]
class ModelFile(XMLFile):
    """
    Represents the overall parameters.xml file.
    """
    def __init__(self, filename):
        # We expect a single 'Analysis' element below Model
        _logger.debug("Loading model file: %s", filename)

        super().__init__(filename, schemaPath='etc/opgee.xsd')

        self.root = self.tree.getroot()
        self.model = Model.from_xml(self.root)
