from opgee import ureg
from .utils_for_tests import load_model_from_str

template = """<?xml version='1.0' encoding='UTF-8'?>
<Model>
  <Analysis name="test">
    <A name="functional_unit">oil</A>
    <A name="GWP_horizon">100</A>
    <A name="GWP_version">AR5</A>

    <Field name="test"/>
  </Analysis>

  <Field name="test" modifies="template">
    <A name="country">{country}</A>
    <A name="downhole_pump">0</A>
    <A name="water_reinjection">1</A>
    <A name="natural_gas_reinjection">1</A>
    <A name="water_flooding">0</A>
    <A name="gas_lifting">1</A>
    <A name="gas_flooding">0</A>
    <A name="steam_flooding">0</A>
    <A name="oil_sands_mine">None</A>
    <A name="name">Girassol</A>
  </Field>
</Model>

"""

def model_for_country(country):
    xml = template.format(country=country)
    model = load_model_from_str(xml)
    return model

def test_model_1(configure_logging_for_tests):
    model = model_for_country('USA')
    field = model.get_field('test')
    T = field.attr('prod_water_inlet_temp')
    assert T == ureg.Quantity(140, 'degF')


def test_model_2(configure_logging_for_tests):
    model = model_for_country('Canada')
    field = model.get_field('test')
    T = field.attr('prod_water_inlet_temp')
    assert T == ureg.Quantity(340, 'degF')
