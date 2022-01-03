import pytest
import os
from lxml import etree as ET
from tempfile import mkdtemp
from .utils_for_tests import path_to_test_file
from opgee.xml_utils import merge_siblings, prettify

def assert_same_xml(x1, x2):
    x1_str = ET.tostring(x1, pretty_print=True).decode("utf-8")
    x2_str = ET.tostring(x2, pretty_print=True).decode("utf-8")
    assert x1_str == x2_str

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
    assert_same_xml(x1, expected)


merged_1 = prettify(ET.XML("""
<Model xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="../../opgee/etc/opgee.xsd">
  <Analysis name="test">
    <Field name="test"/>
  </Analysis>
  <Field name="test">
    <Group>First test</Group>
    <A name="country">USA</A>
    <A name="steam_flooding">1</A>
    <A name="gas_flooding">1</A>
    <A name="sync_attr_1">1</A>
    <A name="sync_attr_2">1</A>
    <Process class="ProcA" desc="Test process 1"/>
    <Process class="ProcB" desc="Test process 2"/>
    <Stream src="ProcA" dst="ProcB">
      <A name="temperature">90.0</A>
      <A name="pressure">150.0</A>
      <Component name="oil" phase="liquid">100</Component>
      <Contains>crude oil</Contains>
    </Stream>
  </Field>
  <Analysis name="other">
    <Field name="other"/>
  </Analysis>
  <Field name="other">
    <A name="country">USA</A>
    <Process class="ProcA" desc="Test process 1"/>
    <Process class="ProcB" desc="Test process 2"/>
    <Stream src="ProcA" dst="ProcB">
      <A name="temperature">90.0</A>
      <A name="pressure">150.0</A>
      <Component name="oil" phase="liquid">100</Component>
      <Contains>crude oil</Contains>
    </Stream>
  </Field>
</Model>
"""))

merged_2 = prettify(ET.XML("""
<Model xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="../../opgee/etc/opgee.xsd">
  <Analysis name="test">
    <Field name="test"/>
  </Analysis>
  <Field name="test">
    <Group>First test</Group>
    <A name="country">USA</A>
    <A name="steam_flooding">1</A>
    <A name="gas_flooding">1</A>
    <A name="sync_attr_1">1</A>
    <A name="sync_attr_2">1</A>
    <Process class="ProcA" desc="Test process 1"/>
    <Process class="ProcB" desc="Test process 2"/>
    <Stream src="ProcA" dst="ProcB">
      <A name="temperature">90.0</A>
      <A name="pressure">150.0</A>
      <Component name="oil" phase="liquid">100</Component>
      <Contains>crude oil</Contains>
    </Stream>
  </Field>
  <Analysis name="other">
    <Field name="other"/>
  </Analysis>
  <Field name="other">
    <A name="country">USA</A>
    <Process class="ProcA" desc="Test process 1">
      <A name="temperature">100.0</A>
      <A name="pressure">185.0</A>
    </Process>
    <Process class="ProcB" desc="Test process 2"/>
    <Stream src="ProcA" dst="ProcB">
      <A name="temperature">99.0</A>
      <A name="pressure">150.0</A>
      <Component name="oil" phase="liquid">111</Component>
      <Contains>crude oil</Contains>
      <Contains>random substance</Contains>
    </Stream>
  </Field>
</Model>
"""))

in1 = path_to_test_file('test_merge_1.xml')
in2 = path_to_test_file('test_merge_2.xml')
in3 = path_to_test_file('test_merge_3.xml')

def opg(cmdline):
    import shlex
    from opgee.tool import main

    # print(f"Running 'opg {cmdline}'")
    argv = shlex.split(cmdline)
    main(argv)


def tmpdir():
    dirname = mkdtemp(prefix='merged_xml_')
    return dirname


@pytest.mark.parametrize(
    "cmdline,expected", [(f'merge -n "{in1}" "{in2}" -o "merged.xml" --overwrite', merged_1),
                         (f'merge -n "{in1}" "{in2}" "{in3}" -o "merged.xml" --overwrite', merged_2)])
def test_merge(cmdline, expected):
    out_dir = tmpdir()
    os.chdir(out_dir)

    opg(cmdline)

    with open(f"{out_dir}/merged.xml", 'rb') as f:
        out_xml = f.read()

    out_tree = prettify(ET.XML(out_xml))
    assert_same_xml(out_tree, expected)
