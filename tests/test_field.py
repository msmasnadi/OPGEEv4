import pytest
from .utils_for_tests import load_model_from_str
from opgee.error import XmlFormatError

model_xml_1 = """
<Model xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="../../opgee/etc/opgee.xsd">

	<Analysis name="test">
	  <A name="functional_unit">oil</A>
	  <A name="GWP_horizon">100</A>
	  <A name="GWP_version">AR5</A>
      <Field name="test1"/>
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

	<Analysis name="test">
	  <A name="functional_unit">oil</A>
	  <A name="GWP_horizon">100</A>
	  <A name="GWP_version">AR5</A>
      <Field name="test1"/>
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

def test_bad_boundary():
    with pytest.raises(XmlFormatError, match=".*UnknownBoundary is not a known boundary name.*"):
       model = load_model_from_str(model_xml_1)

    with pytest.raises(XmlFormatError, match=".*Duplicate declaration of boundary.*"):
       model = load_model_from_str(model_xml_2)

    # model.validate()
    # analysis = model.get_analysis('test')



