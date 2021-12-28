import pytest
from lxml import etree
from opgee.XMLFile import XMLFile
from opgee.error import XmlFormatError
from .utils_for_tests import path_to_test_file

def test_read_xml():
    xml_path = path_to_test_file('test_model.xml')
    xml_file = XMLFile(xml_path, schemaPath='etc/opgee.xsd')
    assert xml_file.getFilename() == xml_path

    root = xml_file.getRoot()
    assert isinstance(root, etree._Element)

    tree = xml_file.getTree()
    assert isinstance(tree, etree._ElementTree)

def test_bad_filename():
    xml_file = 'nonexistent-model.xml'
    schema_path = 'etc/opgee.xsd'
    xml_path = path_to_test_file(xml_file)
    with pytest.raises(XmlFormatError, match=f"Can't read XML file '{xml_path}': .*"):
        XMLFile(xml_path, schemaPath=schema_path)

def test_bad_model():
    xml_file = 'bad_model.xml'
    schema_path = 'etc/opgee.xsd'
    xml_path = path_to_test_file(xml_file)
    with pytest.raises(XmlFormatError, match=f"Validation of '{xml_path}'\n.*using schema '{schema_path}' failed:\n.*"):
        XMLFile(xml_path, schemaPath=schema_path)

# Validation of '.../OPGEEv4/tests/files/bad_model.xml'
#   using schema 'etc/opgee.xsd' failed:
#   Element 'Field': The attribute 'name' is required but missing., line 24
