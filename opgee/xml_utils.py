'''
.. Created 2020 as part of pygcam.
   Imported into opgee on 4/22/21

.. Copyright (c) 2015-2021 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from copy import deepcopy
from io import StringIO
from lxml import etree as ET

def prettify(elt):
    parser = ET.XMLParser(remove_blank_text=True)
    xml = ET.tostring(elt)
    file_obj = StringIO(xml.decode('utf-8'))
    tree = ET.parse(file_obj, parser)
    return tree.getroot()

# Oddly, we must re-parse the XML to get the formatting right.
def write_xml(tree, filename):
    parser = ET.XMLParser(remove_blank_text=True)
    xml = ET.tostring(tree.getroot())
    file_obj = StringIO(xml.decode('utf-8'))
    tree = ET.parse(file_obj, parser)

    tree.write(filename, pretty_print=True, xml_declaration=True)

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

def merge_element(parent, new_elt):
    """
    Add an element if none of parent's children has the same tag and attributes
    as element. If a match is found, add element's children to those of the
    matching element.
    """
    for sibling in parent:
        if match_element(new_elt, sibling):
            if new_elt.attrib.get('delete', '0') == '1':
                parent.remove(sibling)
            else:
                merge_elements(sibling, new_elt.getchildren())
            return

    # if it wasn't merged, append it to parent
    parent.append(deepcopy(new_elt))

def merge_elements(parent, elt_list):
    """
    Add each element in elt_list to parent if none of parent's children has the same tag
    and attributes as element. If a match is found, merge element's children with those
    of the matching element, recursively.
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


def ElementWithText(tag, text, **kwargs):
    elt = ET.Element(tag, **kwargs)
    elt.text = str(text)
    return elt

def SubElementWithText(parent, tag, text, **kwargs):
    elt = ElementWithText(tag, text, **kwargs)
    parent.append(elt)
    return elt
