#!/usr/bin/env python
#
# Read opgee.xml and write out a sorted list of unique stream content names
#
from lxml import etree as ET

from opgee.config import getParam
from opgee.pkg_utils import resourceStream
from opgee.XMLFile import XMLFile

def main():
    opgee_xml = getParam('OPGEE.ModelFile')
    base_stream = resourceStream(opgee_xml, stream_type='bytes', decode=None)
    xml_file = XMLFile(base_stream, schemaPath='etc/opgee.xsd')
    root = xml_file.getRoot()

    # use a Set to store unique values
    contents = {elt.text for elt in root.findall(".//Stream/Contains")}
    for txt in sorted(contents):
        print(txt)

if __name__ == '__main__':
    main()
