#
# OPGEE ModelFile class
#
# Author: Richard Plevin
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import os
from copy import deepcopy
from pathlib import Path

from .XMLFile import XMLFile
from .attributes import AttrDefs
from .config import getParam, unixPath, pathjoin
from .core import Timer
from .error import OpgeeException, XmlFormatError
from .log import getLogger
from .model import Model
from .pkg_utils import resourceStream
from .process import reload_subclass_dict
from .stream import Stream
from .utils import loadModuleFromPath, splitAndStrip, mkdirs, is_relpath
from .xml_utils import merge_elements, save_xml

_logger = getLogger(__name__)

class ModelCache(object):
    """
    Support for optimizing reading / running fields from large (i.e., thousands)
    of Fields from Model files generated from XML. XMLFile instances are cached by
    pathname to avoid rereading large files.
    """
    model_file_cache = {}

    @classmethod
    def decache(cls):
        """
        Empty the cache of XMLFile instances representing OPGEE Models.
        """
        cls.model_file_cache.clear()

    @classmethod
    def get_xml_file(cls, model_xml):
        """
        If the file ``model_xml`` is not known in the cache, load it and
        store it in the cache. Return the cached XMLFile object.

        :param model_xml: (str) pathname of an XML file
        :return: (XMLFile) representing the model XML
        """
        try:
            obj = cls.model_file_cache[model_xml]
        except KeyError:
            obj = XMLFile(model_xml, schemaPath='etc/opgee.xsd')
            cls.model_file_cache[model_xml] = obj

        return obj

def model_analysis_names(model_xml):
    """
    Return the names of all <Analysis> elements in the file ``model_xml``.

    :param model_xml: (str) the pathname of an OPGEE model XML file.
    :return: (list of str) the names of the analyses found
    """
    xml_file_obj = ModelCache.get_xml_file(model_xml)

    root = xml_file_obj.getRoot()
    analyses = root.xpath(f'/Model/Analysis/@name')
    return analyses

def fields_for_analysis(model_xml, analysis_name):
    """
    Return a list of the names of Fields in the Analysis
    named ``analysis_name`` in the model XML file ``model_xml``.

    :param model_xml: (str) the pathname of an OPGEE model XML file.
    :param analysis_name: (str) the name of an Analysis
    :return: (list of str) the names of all the Fields in the given
        Analysis.
    """
    timer = Timer('fields_for_analysis')

    xml_file_obj = ModelCache.get_xml_file(model_xml)

    root = xml_file_obj.getRoot()
    xpath = f'/Model/Analysis[@name="{analysis_name}"]/Field/@name'
    fields = root.xpath(xpath)

    _logger.debug(timer.stop())
    return fields

# TBD: this is used only by extract_model(..., as_string=True) so perhaps
#   this can be simplified or split into two functions
def _get_xml_str(model_xml, analysis_name, field_name, with_model_elt=False):
    """
    Extract an XML model file as a string, for the Field ``field_name`` from
    the Analysis ``analysis_name`` in the model XML file ``model_xml``.

    :param model_xml: (str) the pathname of an OPGEE model XML file
    :param analysis_name: (str) the name of an Analysis
    :param field_name: (str) the name of the Field to extract
    :return: (str) if ``as_string`` is False, returns the pathname of a file
        under {OPGEE.TempFile}/extracted_xml. Note that it's the caller's
        responsibility to remove the temp file. If ``as_string`` is True, a
        string representation of the model XML is returned.
    """
    from lxml import etree as ET

    xml_file_obj = ModelCache.get_xml_file(model_xml)
    root = xml_file_obj.getRoot()

    _logger.debug(f"Extracting field {field_name}")

    found = root.xpath(f'/Model/Analysis[@name="{analysis_name}"]/Field[@name="{field_name}"]')
    if not found:
        raise OpgeeException(f"Field '{field_name}' was not found under Analysis '{analysis_name}'")

    # xpath() returns a list
    if len(found) > 1:
        raise OpgeeException(f"Field '{field_name}' appears multiple times in model XML")

    extracted_field = found[0]

    # Create a model with just the extracted Field and surrounding elements
    model = ET.Element('Model')
    analysis = ET.SubElement(model, 'Analysis', name=analysis_name)
    analysis.append(deepcopy(extracted_field))

    xml_string = ET.tostring(model, pretty_print=True, encoding="unicode")
    return xml_string, model if with_model_elt else xml_string

def _get_tmp_xml_file(model_xml, analysis_name, field_name):
    """
    Save an XML model file to the temp folder identified by config variable
    OPGEE.TempDir (in a subdirectory "extracted_xml") by extracting the Field
    named ``field_name`` from the Analysis named ``analysis_name`` in the model
    XML file ``model_xml``.

    :param model_xml: (str) the pathname of an OPGEE model XML file
    :param analysis_name: (str) the name of an Analysis
    :param field_name: (str) the name of the Field to extract
    :return: (str) returns the pathname of a file under
        {OPGEE.TempFile}/extracted_xml. Note that it's the caller's
        responsibility to remove the temp file.
    """
    from lxml import etree as ET

    xml_string, model = _get_xml_str(model_xml, analysis_name, field_name,
                                     with_model_elt=True)

    # replaces spaces with underscores
    field_name = field_name.replace(' ', '_')
    tmp_dir = pathjoin(getParam('OPGEE.TempDir'), 'extracted_xml')
    mkdirs(tmp_dir)
    xml_file = pathjoin(tmp_dir, field_name + '.xml')

    # Write the XML to a file in tmp_dir
    tree = ET.ElementTree(model)
    tree.write(xml_file, xml_declaration=True, pretty_print=True, encoding='utf-8')

    return xml_file


def extract_model(model_xml, analysis_name, field_names):
    """
    Generator to return temp files with extracted model for each Field in
    `field_names`` or all the Fields in ``analysis_name`` if ``field_names``
    is None.

    :param model_xml: (str) pathname to (presumably large) Model xml file.
    :param analysis_name: (str) the name of the analysis to use
    :param field_names: (list of str) names of Fields to extract. If None,
        all Fields in the given Analysis are extracted.
    :param as_string: (bool) whether to return a string representation of the
       model XML or a pathname to a temporary file (the default).
    :return: (str, str) a tuple of two strings: the next Field name a string
        representation of the model XML for that Field.
    """
    field_names = field_names or fields_for_analysis(model_xml, analysis_name)

    for field_name in field_names:
        yield field_name, _get_xml_str(model_xml, analysis_name, field_name)


class ModelFile(XMLFile):
    """
    Represents the overall opgee.xml file.
    """

    # Remember paths loaded so we avoid reloading them and re-defining Process subclasses
    _loaded_module_paths = dict()

    _loaded_stream_components = False
    _loaded_user_classes = False

    def __init__(self, pathnames, xml_string=None, add_stream_components=True,
                 use_class_path=True, use_default_model=True,
                 instantiate_model=True, save_to_path=None,
                 analysis_names=None, field_names=None):
        """
        Several steps are performed, some of which are dependent on the function's parameters:

        1. If `add_stream_components` is True, load any extra stream components defined by config file
        variable "OPGEE.StreamComponents".

        2. Reads the input XML filename using either from `pathnames` (if not None or empty list)
        or from the default model. If ``use_default_model`` is True, etc/opgee.xml is loaded first
        and other XML files are merged in, in the order given.

        3. If `use_class_path` is True, loads any Python files found in the path list defined by
        "OPGEE.ClassPath". Note that all classes referenced by the XML must be defined internally
        by opgee, or in the user's files indicated by "OPGEE.ClassPath".

        4. Construct the model data structure from the input XML file and store the result in `self.model`.

        :param pathnames: (str, or list or tuple of str) the name(s) of the file(s) to read.
           If None or empty list, ``use_default_model`` must be True, or ``xml_string`` must be used.
        :param xml_string: (str) text representation of XML to use instead of ``pathnames``. If provided,
            this string must comprise the full model XML, including attribute definitions. (That is, the
            file "etc/attributes.xml" will not be read. Also, no "final" XML is written out and the
            ``save_to_path`` argument is ignored (and no default path is used). Note that ``xml_string``
            is used primarily to reduce disk I/O in Monte Carlo mode.
        :param add_stream_components: (bool) whether to load additional `Stream` components using the
           value of config parameter "OPGEE.StreamComponents".
        :param use_class_path: (bool) whether to load custom python classes from the path indicated by
           config file variable "OPGEE.ClassPath".
        :param use_default_model: (bool) whether to load the built-in files "etc/opgee.xml" and
           "/etc/attributes.xml".
        :param instantiate_model: (bool) whether to parse the merged XML to create a ``Model``
            instance.
        :param save_to_path: (str) If provided, the final merged XML will be written to this pathname.
        :param analysis_names: (list of str) the names of Analyses to include. If not None, only
            the given named Analysis elements will be loaded.
        :param field_names: (list of str) the names of Fields to include. Any other fields are
            ignored when building the model from the XML. (Avoids long model build times for
            Monte Carlo simulations on a large number of fields.)
        """
        load_timer = Timer('ModelFile load XML')

        source = "XML string" if xml_string else pathnames
        _logger.debug(f"Loading model from: {source}")

        if not isinstance(pathnames, (list, tuple)):
            pathnames = [] if pathnames is None else [pathnames]

        if not (pathnames or use_default_model or xml_string):
            raise OpgeeException(f"ModelFile: no model XML file or string specified")

        opgee_xml = getParam('OPGEE.ModelFile')           # default is 'etc/opgee.xml'
        attributes_xml = getParam('OPGEE.AttributesFile') # default is 'etc/attributes.xml'

        base_stream = base_path = None

        # Assemble a list of built-in and user XML files to read and merge
        if use_default_model:
            if is_relpath(opgee_xml):
                base_stream = resourceStream(opgee_xml, stream_type='bytes', decode=None)
            else:
                base_path = opgee_xml
        else:
            base_path = pathnames.pop(0) if pathnames else None

        # Use superclass XMLFile to load base file we will merge into
        super().__init__(base_stream or base_path, xml_string=xml_string, schemaPath='etc/opgee.xsd')
        self.root = base_root = self.tree.getroot()

        # Read and validate the format of any other input files.
        xml_files = [XMLFile(path, schemaPath='etc/opgee.xsd') for path in pathnames]

        if not xml_string:
            # Push the XMLFile for attributes.xml onto the front of 'xml_files'
            attr_stream_or_path = (resourceStream(attributes_xml, stream_type='bytes', decode=None)
                                   if is_relpath(attributes_xml) else attributes_xml)

            xml_file = XMLFile(attr_stream_or_path, schemaPath='etc/opgee.xsd')
            xml_files.insert(0, xml_file)

        # Read all XML files and merge everything below <Model> into base_root
        for xml_file in xml_files:
            root = xml_file.getRoot()
            merge_elements(base_root, root[:])

        # Find Fields with modifies="..." attribute, copy the indicated Field, merge in the
        # elements under the Field with modifies=, and replace elt. This is useful for
        # debugging and storing the expanded "final" XML facilitates publication and replication.
        found = base_root.xpath('//Analysis/Field[@modifies]')
        for elt in found:
            attrib = elt.attrib
            modifies = attrib['modifies']
            new_name = attrib['name']

            if base_root.find(f"Field[@name='{new_name}']") is not None:
                raise XmlFormatError(f"Can't copy field '{modifies}' to '{new_name}': a field named '{new_name}' already exists.")

            to_copy = base_root.find(f"Field[@name='{modifies}']")

            if to_copy is None:
                raise XmlFormatError(f"Can't create field '{new_name}': modified field '{modifies}' not found.")

            # Change attribute from "modifies" to "modified" to record action and avoid redoing it
            del attrib['modifies']
            attrib['modified'] = modifies

            copied = deepcopy(to_copy)      # don't modify the original
            copied.attrib.update(attrib)    # copy elt's attributes into `copied`

            # N.B. Elements don't match unless *all* attribs are identical. Maybe match only on tag and name attribute??
            merge_elements(copied, elt[:])      # merge elt's children into `copied`
            base_root.append(copied)            # add the copy to the Model

            # The <Field> elements under analysis just need to refer to the field by name
            # We can remove all the other items after merging them above.
            for child in elt:
                elt.remove(child)

        # TBD: currently each worker overwrites the same file. Maybe just skip this next line? Skip if running MCS?
        if not xml_string:
            # function argument overrides config file variable
            save_to_path = getParam('OPGEE.XmlSavePathname') if save_to_path is None else save_to_path

            # Save the merged file if indicated
            if save_to_path:
                save_xml(save_to_path, base_root, backup=True)

        # There must be exactly one <AttrDefs> as child of <Model>
        found = base_root.findall('AttrDefs')
        if found is None or len(found) == 0:
            raise XmlFormatError(f"Missing <AttrDefs> as child of <Model> in '{pathnames}'")

        elif len(found) > 1:
            raise XmlFormatError("Multiple <AttrDefs> appear as children of <Model> in '{pathnames}'")

        AttrDefs.load_attr_defs(found[0])

        # Process user configuration settings
        if add_stream_components:
            extra_components = getParam('OPGEE.StreamComponents')   # DOCUMENT this config parameter
            if extra_components:
                names = splitAndStrip(extra_components, ',')
                Stream.extend_components(names)

        def _load_from_path(module_path):
            module_path = unixPath(module_path, abspath=True)
            module = loadModuleFromPath(module_path)
            self._loaded_module_paths[module_path] = module

        # Load user classes, if indicated in config file, prior to parsing the XML structure
        if use_class_path:
            class_path = getParam('OPGEE.ClassPath')
            paths = [Path(path) for path in class_path.split(os.path.pathsep) if path]
            for path in paths:
                if path.is_dir():
                    for module_path in path.glob('*.py'):  # load all .py files found in directory
                        _load_from_path(module_path)
                else:
                    print(f"Loading module from '{path}'")
                    _load_from_path(path)

            if paths:
                reload_subclass_dict()

        _logger.debug(load_timer.stop())

        # the merge subcommand specifies instantiate_model=False, but normally the model is loaded.
        if instantiate_model:
            build_timer = Timer('ModelFile build model')
            _logger.debug(build_timer)
            self.model = model = Model.from_xml(base_root, analysis_names=analysis_names,
                                                field_names=field_names)
            _logger.debug(build_timer.stop())

            model.validate()

            # Show the list of paths read in the GUI
            pathnames.insert(0, opgee_xml if base_stream else base_path)
            model.set_pathnames(pathnames)
        else:
            self.model = None

    @classmethod
    def from_xml_string(cls, xml_string, add_stream_components=True,
                 use_class_path=True, use_default_model=True,
                 analysis_names=None, field_names=None):
        """
        Create a ModelFile instance from an XML string representing the XML model structure.
        This provides an alternative to storing the model in a separate XML file, e.g., for
        keeping all test code in one Python file.

        All keyword args are passed through to ModelFile().

        :param xml_string: (str) String representation of a <Model> structure and all
            nested elements.
        :return: (opgee.ModelFile) the ModelFile instance.
        """
        import os
        from tempfile import mkstemp

        fd, tmp_file = mkstemp(suffix='.xml', text=True)
        os.write(fd, str.encode(xml_string))
        os.close(fd)

        try:
            model_file = ModelFile([tmp_file], # TBD: use xml_string=xml_string instead of tmp_file
                                   add_stream_components=add_stream_components,
                                   use_class_path=use_class_path,
                                   use_default_model=use_default_model,
                                   analysis_names=analysis_names,
                                   field_names=field_names,
                                   instantiate_model=True,
                                   save_to_path="")     # ensures no saving. Passing None falls back to config var
        except Exception as e:
            raise XmlFormatError(f"Failed to create ModelFile from string: {e}")

        finally:
            os.remove(tmp_file)

        return model_file
