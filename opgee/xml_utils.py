'''
.. Created as part of pygcam (2020)
   Imported into opgee (2021)

.. Copyright (c) 2015-2022 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from copy import deepcopy
from io import StringIO
from lxml import etree as ET
from .log import getLogger
from .error import OpgeeException

_logger = getLogger(__name__)


def str_to_xml(s):
    elt = ET.XML(s)
    parser = ET.XMLParser(remove_blank_text=True)
    xml = ET.tostring(elt)
    file_obj = StringIO(xml.decode('utf-8'))
    tree = ET.parse(file_obj, parser)
    return tree.getroot()


def save_xml(path, root, backup=False, overwrite=False):
    from pathlib import Path
    import os

    if path:
        p = Path(path)
        if p.exists():
            if backup:
                backup = path + '~'
                os.rename(path, backup)
            elif not overwrite:
                raise OpgeeException(f"save_xml: file exists: '{path}'; to overwrite specify backup=True or overwrite=True")

        _logger.info(f"Writing '{path}'")
        tree = ET.ElementTree(root)
        tree.write(path, xml_declaration=True, pretty_print=True, encoding='utf-8')
    else:
        # for debugging only
        ET.dump(root, pretty_print=True) # pragma: no cover


def attr_to_xml(fields, dtypes, xml_path, analysis_name, modifies='default'):
    from lxml import etree as ET
    import numpy as np

    known_types = {'int' : int, 'float' : float, 'str' : str}

    root = ET.Element('Model')
    analysis = ET.SubElement(root, 'Analysis', attrib={'name' : analysis_name})

    # Convert fields to xml
    for field_name, col in fields.iteritems():
        field = ET.SubElement(analysis, 'Field',
                              attrib={'name' : field_name, 'modifies' : modifies})

        for attr, value in col.items():

            # don't include unspecified attributes
            try:
                if np.isnan(value):
                    continue
            except:
                pass  # np.isnan() fails for non-numeric types; ignore it

            if value == '' or value is None:
                continue

            a = ET.SubElement(field, 'A', attrib={'name': attr})
            dtype = dtypes[attr]
            type_fn = known_types[dtype]
            try:
                a.text = str(type_fn(value))
            except Exception:
                _logger.error(f"Failed to coerce '{value}' to {dtype} for attribute '{attr}'")

    save_xml(xml_path, root, overwrite=True)

# Deprecated (currently unused)
# Oddly, we must re-parse the XML to get the formatting right.
# def write_xml(tree, filename):
#     parser = ET.XMLParser(remove_blank_text=True)
#     xml = ET.tostring(tree.getroot())
#     file_obj = StringIO(xml.decode('utf-8'))
#     tree = ET.parse(file_obj, parser)
#
#     tree.write(filename, pretty_print=True, xml_declaration=True)

#
# TBD: Elements don't match unless *all* attribs are identical. Maybe match only on tag and name attribute??
#
# Surface level (tag and attribute) comparison of elements
def match_element(elt1, elt2):
    if elt1.tag != elt2.tag:
        return False

    attr1 = elt1.attrib
    attr2 = elt2.attrib

    # if len(attr1) != len(attr2):
    #     return False

    try:
        for key, value in attr1.items():
            if key != 'delete' and value != attr2[key]:
                return False
    except KeyError:
        return False

    return True

def elt2str(elt):
    attribs = ' '.join([f'{key}="{value}"' for key, value in elt.attrib.items()])
    s = f"<{elt.tag} {attribs}>"
    return s

def merge_element(parent, new_elt):
    """
    Add an element if none of parent's children has the same tag and attributes
    as element. If a match is found, add element's children to those of the
    matching element.
    """
    for sibling in parent:
        # _logger.debug(f"merge_element: new_elt {element_string(new_elt)} to sibling {element_string(sibling)}")
        if match_element(new_elt, sibling):
            # _logger.debug(f"matched: {elt2str(new_elt)}  and  {elt2str(sibling)}")
            if new_elt.attrib.get('delete', '0') == '1':
                _logger.debug(f"Deleting {elt2str(sibling)}")
                parent.remove(sibling)
            else:
                sibling.text = new_elt.text
                merge_elements(sibling, new_elt.getchildren())
            return

        # _logger.debug(f"NOT matched: {element_string(new_elt)}  and  {element_string(sibling)}")

    # if it wasn't merged, append it to parent
    _logger.debug(f"Appending {elt2str(new_elt)} to {elt2str(parent)}")
    parent.append(deepcopy(new_elt))

def merge_elements(parent, elt_list):
    """
    Add each element in `elt_list` to parent if none of parent's children has the same tag
    and attributes as `elt`. If a match is found, merge elt's children with those of the
    the matching element, recursively.
    """
    for elt in elt_list:
        merge_element(parent, elt)

def merge_siblings(elt1, elt2):
    """
    Merge elt2 into elt1.

    :return: none (elt1 is modified)
    """
    if not match_element(elt1, elt2):
        return # fails silently

    merge_elements(elt1, elt2[:])
