import pytest
from opgee import ureg
from opgee.model_file import ModelFile
from opgee.process import Process

xml_string = """
<Model xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="../../opgee/etc/opgee.xsd">
  <Analysis name="test">
    <Field name="test"/>
    <A name="boundary">Transportation</A>
  </Analysis>
  
  <Field name="test">
    <Process class="Boundary_proc_1"/>
    <Process class="Boundary_proc_2"/>
    <Process class="Boundary_proc_3"/>
    <Process class="Boundary_proc_4"/>
    <Process class="Boundary" boundary="Production"/>
    <Process class="Boundary" boundary="Transportation"/>
    
    <Stream src="Boundary_proc_1" dst="Boundary_proc_2">
      <Component name="oil" phase="liquid">100</Component>
      <Contains>crude oil</Contains>
    </Stream>
    
    <Stream src="Boundary_proc_1" dst="Boundary_proc_3">
      <Contains>natural gas</Contains>
      <Component name="C1" phase="gas">987</Component>
    </Stream>

    <Stream src="Boundary_proc_2" dst="ProductionBoundary">
      <Contains>crude oil</Contains>
    </Stream>
        
    <Stream src="Boundary_proc_3" dst="ProductionBoundary">
      <Contains>natural gas</Contains>
    </Stream>
    
    <Stream src="ProductionBoundary" dst="Boundary_proc_4" name="oil stream 1">
      <Contains>crude oil</Contains>
    </Stream>
    <Stream src="ProductionBoundary" dst="Boundary_proc_4" name="gas stream 1">
      <Contains>natural gas</Contains>
    </Stream>
    
    <Stream src="Boundary_proc_4" dst="TransportationBoundary" name="oil stream 2">
      <Contains>crude oil</Contains>
    </Stream>
    <Stream src="Boundary_proc_4" dst="TransportationBoundary" name="gas stream 2">
      <Contains>natural gas</Contains>
    </Stream>
    
  </Field>
</Model>
"""


class Boundary_proc_1(Process):
    def run(self, analysis):
        pass


class Boundary_proc_2(Process):
    def run(self, analysis):
        in_stream = self.find_input_stream("crude oil")
        if in_stream.is_uninitialized():
            return
        out_stream = self.find_output_stream("crude oil")
        out_stream.copy_flow_rates_from(in_stream)


class Boundary_proc_3(Process):
    def run(self, analysis):
        in_stream = self.find_input_stream("natural gas")
        if in_stream.is_uninitialized():
            return
        out_stream = self.find_output_stream("natural gas")
        out_stream.copy_flow_rates_from(in_stream)


class Boundary_proc_4(Process):
    def run(self, analysis):
        for content in ("crude oil", "natural gas"):
            in_stream = self.find_input_stream(content)
            if in_stream.is_uninitialized():
                return
            out_stream = self.find_output_stream(content)
            out_stream.copy_flow_rates_from(in_stream)


def test_intermediate_boundary():
    model_file = ModelFile.from_xml_string(xml_string)
    model = model_file.model
    analysis = model.get_analysis('test')
    analysis.run(compute_ci=False)
    field = model.get_field('test')
    boundary_proc = field.boundary_process(analysis)
    stream = boundary_proc.sum_input_streams()
    gas_rate = stream.gas_flow_rate('C1')
    oil_rate = stream.liquid_flow_rate('oil')
    assert gas_rate == ureg.Quantity(987.0, 't/d') and oil_rate == ureg.Quantity(100.0, 't/d')

    energy_flow_rate = field.boundary_energy_flow_rate(analysis)
    assert energy_flow_rate == ureg.Quantity(pytest.approx(4030.009), "mmbtu/day")
