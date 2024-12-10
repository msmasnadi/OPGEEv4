import pytest

from opgee.error import XmlFormatError
from opgee.units import ureg

from .test_processes import approx_equal
from .utils_for_tests import load_model_from_str, load_test_model

model_xml_1 = """
<Model xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="../../opgee/etc/opgee.xsd">
	<A name="skip_validation">1</A>

	<Analysis name="test">
	  <A name="functional_unit">oil</A>
	  <A name="GWP_horizon">100</A>
	  <A name="GWP_version">AR5</A>
      <FieldRef name="test1"/>
	</Analysis>

	<Field name="test1">
		<A name="country">USA</A>
		<Process class="After"/>
		<Process class="ProcA" desc="Test process 1"/>
		<Process class="ProcB" desc="Test process 2"/>
		<Process class="Boundary" boundary="UnknownBoundary"/>

		<Stream src="ProcB" dst="ProductionBoundary"/>
	</Field>

</Model>
"""

model_xml_2 = """
<Model xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="../../opgee/etc/opgee.xsd">
	<A name="skip_validation">1</A>

	<Analysis name="test">
	  <A name="functional_unit">oil</A>
	  <A name="GWP_horizon">100</A>
	  <A name="GWP_version">AR5</A>
      <FieldRef name="test1"/>
	</Analysis>

	<Field name="test1">
		<A name="country">USA</A>
		<Process class="After"/>
		<Process class="ProcA" desc="Test process 1"/>
		<Process class="ProcB" desc="Test process 2"/>
		<Process class="Boundary" boundary="Production"/>
		<Process class="Boundary" boundary="Production"/>

		<Stream src="ProcB" dst="ProductionBoundary"/>
	</Field>

</Model>
"""


@pytest.fixture(scope="module")
def test_field(configure_logging_for_tests):
    return load_test_model('test_fields.xml',
                           use_default_model=True) # this is required since test_fields references "template" field


def test_component_fugitive(test_field):
    analysis = test_field.get_analysis('test_fugitive')
    oilfield = analysis.get_field('test_component_fugitive_oilfield')
    oilfield_component_fugitive_df = oilfield.component_fugitive_table

    assert approx_equal(oilfield_component_fugitive_df['Separation'], ureg.Quantity(3.053545e-05, "frac"))
    assert approx_equal(oilfield_component_fugitive_df['CrudeOilStorage'], ureg.Quantity(0.931951, "frac"))
    assert approx_equal(oilfield_component_fugitive_df['DownholePump'], ureg.Quantity(0.000410132, "frac"))

    gasfield = analysis.get_field('test_component_fugitive_gasfield')
    gasfield_component_fugitive_df = gasfield.component_fugitive_table

    assert approx_equal(gasfield_component_fugitive_df['Separation'], ureg.Quantity(3.77813e-5, "frac"))
    assert approx_equal(gasfield_component_fugitive_df['CrudeOilStorage'], ureg.Quantity(0.4323671, "frac"))
    assert approx_equal(gasfield_component_fugitive_df['DownholePump'], ureg.Quantity(7.220268674108583e-05, "frac"))


def test_bad_boundary():
    with pytest.raises(XmlFormatError, match=".*UnknownBoundary is not a known boundary name.*"):
        model = load_model_from_str(model_xml_1)

    with pytest.raises(XmlFormatError, match=".*duplicate.*"):
        model = load_model_from_str(model_xml_2)

    # with pytest.raises(XmlFormatError, match=".*Duplicate declaration of boundary.*"):
    #     model = load_model_from_str(model_xml_2)

    # model.validate()
    # analysis = model.get_analysis('test')
