from opgee.XMLFile import XMLFile
from opgee.core import from_xml

def main():
    m = XMLFile('/Users/rjp/repos/opgee/opgee/etc/opgee.xml', schemaPath='etc/opgee.xsd')
    root = m.tree.getroot()

    analysis = root.find('Analysis')
    attrs = analysis.findall('A')
    attr = attrs[0]

    from opgee.core import A
    obj = A.from_xml(analysis, attr)

    model = from_xml(None, root)
    print(model)

main()
