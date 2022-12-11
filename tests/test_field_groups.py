import pytest
from .utils_for_tests import load_model_from_str

field_groups_model_xml = """
<Model xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="../../opgee/etc/opgee.xsd">

	<Analysis name="test">
	  <A name="functional_unit">oil</A>
	  <A name="GWP_horizon">100</A>
	  <A name="GWP_version">AR5</A>
	  <Group regex="1">.*Foo.*</Group>
	</Analysis>

	<Field name="test1">
		<Group>Foo</Group>
		<A name="country">USA</A>
		<Process class="After"/>

		<Process class="ProcA" desc="Test process 1"/>
		<Process class="ProcB" desc="Test process 2"/>
		<Process class="Boundary" boundary="Production"/>

		<Stream src="ProcB" dst="ProductionBoundary"/>
	</Field>

	<Field name="test2">
		<Group>MatchesFooAlso</Group>
		<A name="country">USA</A>

		<Process class="ProcA" desc="Test process 1"/>
		<Process class="ProcB" desc="Test process 2"/>
		<Process class="Boundary" boundary="Production"/>

		<Stream src="ProcB" dst="ProductionBoundary"/>
	</Field>

	<Field name="test3">
		<Group>Bar</Group>
		<A name="country">USA</A>

		<Process class="ProcA" desc="Test process 1"/>
		<Process class="ProcB" desc="Test process 2"/>
		<Process class="Boundary" boundary="Production"/>

		<Stream src="ProcB" dst="ProductionBoundary"/>
	</Field>

</Model>
"""

def test_field_groups():
    field_groups_model = load_model_from_str(field_groups_model_xml)
    field_groups_model.validate()

    analysis = field_groups_model.get_analysis('test')
    # Pattern should match only fields 'test1' and 'test2', and not 'test3'
    assert analysis.get_field('test1') and analysis.get_field('test2') and not analysis.get_field('test3', raiseError=False)


