from opgee.xml_utils import merge_siblings, prettify
from lxml import etree as ET

def test_merge_siblings():
    x1 = prettify(ET.XML("""
    <foo>
        <bar>
            <baz name="horace">abcdef</baz>
            <baz name="a">xyz</baz>
            <baz name="c">lmnop</baz>            
        </bar>
    </foo>"""))

    x2 = prettify(ET.XML("""
    <foo>
        <bar>
            <baz name="b">abc</baz>
            <baz name="c" delete="1"/>
            <baz name="c">replaced</baz>    
        </bar>
    </foo>"""))

    expected = prettify(ET.XML("""
    <foo>
        <bar>
            <baz name="horace">abcdef</baz>
            <baz name="a">xyz</baz>
            <baz name="b">abc</baz>
            <baz name="c">replaced</baz>
      </bar>
    </foo>
    """))

    merge_siblings(x1, x2)

    x1_str = ET.tostring(x1, pretty_print=True).decode("utf-8")
    expected_str = ET.tostring(expected, pretty_print=True).decode("utf-8")

    assert x1_str == expected_str
