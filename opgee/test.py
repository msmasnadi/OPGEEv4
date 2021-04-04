from opgee.XMLFile import XMLFile
from opgee.core import from_xml
from opgee.utils import resourceStream

def main():
    stream = resourceStream('etc/opgee.xml', stream_type='bytes', decode=None)
    m = XMLFile(stream, schemaPath='etc/opgee.xsd')
    root = m.tree.getroot()

    analysis = root.find('Analysis')
    attrs = analysis.findall('A')

    if len(attrs):
        attr = attrs[0]

        from opgee.core import A
        obj = A.from_xml(analysis, attr)

        model = from_xml(None, root)
        print(model)


main()
