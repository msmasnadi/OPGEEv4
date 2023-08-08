from pathlib import Path
import pytest
from io import StringIO

from opgee.error import McsUserError
from opgee.mcs.simulation import read_distributions, Simulation, Distribution
from opgee.mcs.parameter_list import ParameterList
from opgee.tool import opg

from .utils_for_tests import tmpdir, path_to_test_file


def test_distro_xml():
    param_list = ParameterList.load()
    assert param_list

def test_good_distros_xml():
    xml_string = """
<ParameterList xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xsi:noNamespaceSchemaLocation="parameter-schema.xsd">

  <Parameter name="binary">
    <Distribution>
      <Binary prob_of_yes="0.95"/>
    </Distribution>
  </Parameter>

  <Parameter name="uniform">
    <Distribution>
      <Uniform min="10" max="50"/>
    </Distribution>
  </Parameter>
  
  <Parameter name="lognormal">
    <Distribution>
      <Lognormal log_mean="38" log_stdev="22"/>
    </Distribution>
  </Parameter>
  
  <Parameter name="triangle" active="1">
    <Distribution>
      <Triangle min="1" mode="2.8" max="5"/>
    </Distribution>
  </Parameter>  
  
  <Parameter name="inactive" active="0">
    <Distribution>
      <Triangle min="1" mode="2.8" max="5"/>
    </Distribution>
  </Parameter>

  <Parameter name="normal" active="1">
    <Distribution>
      <Normal mean="0" stdev="1"/>
    </Distribution>
  </Parameter>

  <Parameter name="choice_1">
    <Distribution>
      <Choice>
        <!-- NOTE: probabilities were added here just to show the feature -->
        <Value prob="0.2">Low</Value>
        <Value prob="0.4">Med</Value>
        <Value prob="0.2">High</Value>
      </Choice>
    </Distribution>
  </Parameter>
  
  <Parameter name="choice_2">
    <Distribution>
      <Choice>
        <Value>Low carbon</Value>
        <Value>Med carbon</Value>
        <Value>High carbon</Value>
      </Choice>
    </Distribution>
  </Parameter>

  <Parameter name="WOR">
    <Distribution>
      <DataFile>mcs/etc/all_wor.csv</DataFile>
    </Distribution>
  </Parameter>  
</ParameterList>
    """
    params = ParameterList.load(xml_string=xml_string)

    assert len(params.parameters()) == 8
    assert params.parameter("inactive") is None

    p = params.parameter("triangle")
    assert p.rv.dist.name == 'triang'

    p = params.parameter("normal")
    assert p.rv.dist.name == 'norm'

    p = params.parameter("lognormal")
    assert p.rv.dist.name == 'lognorm'

    p = params.parameter("uniform")
    assert p.rv.dist.name == 'uniform'


analysis_name = 'test-mcs'
field_name = 'test-mcs'
model_file = path_to_test_file('test_mcs.xml')
sim_dir = tmpdir('test-mcs')
trials = 100

header = "variable_name,distribution_type,mean,SD,low_bound,high_bound,prob_of_yes,default_value,pathname,notes\n"

def read_string_distros(data):
    """Read parameter distributions from a list of strings formatted as CSV data"""
    csv = StringIO(header + '\n'.join(data))
    Distribution.instances.clear()              # empty the distros so we read new data without stale info
    read_distributions(pathname=csv)

def test_good_distros():
    data = (
        "foo,uniform,0,0,40,80,,,,",
        "Analysis.bar,normal,100,30,,,,,,",
    )
    read_string_distros(data)
    assert len(Distribution.instances) == len(data)
    assert (foo := Distribution.distro_by_name('foo'))
    assert str(foo).startswith('<Distribution ')

    assert (bar := Distribution.distro_by_name('Analysis.bar'))

    assert bar.class_name == 'Analysis' and bar.attr_name == "bar"

def test_bad_distros():
    data = (
        "foo,uniform,0,0,40,40,,,,",    # high == low
        "bar,normal,100,0,,,,,,",       # stdev is zero
        "boo,lognormal,100,0,,,,,,",    # stdev is zero
        "buz,unknown-distro,,,,,,,,",   # unknown distro
     )
    read_string_distros(data)

    assert len(Distribution.instances) == 0 # all should be ignored


def test_missing_analysis():
    with pytest.raises(McsUserError, match="Analysis '.*' was not found"):
        Simulation.new(sim_dir, [], analysis_name + "_Not_A_Valid_Name_", trials,
                       overwrite=True, field_names=[field_name])

def test_gensim():
    cmdline = f'gensim -t {trials} -s {sim_dir} -a test-mcs -f {field_name} -m {model_file} --overwrite'
    opg(cmdline)

    sim = Simulation(sim_dir)
    df = sim.field_trial_data(field_name)
    assert len(df) == trials


def test_simulation():
    read_distributions(pathname=None)
    assert all([isinstance(d, Distribution) for d in Distribution.distributions()])

    sim = Simulation.new(sim_dir, model_file, analysis_name, trials,
                         overwrite=True, field_names=[field_name])

    top_dir = Path(sim_dir)
    field_dir = top_dir / field_name
    assert field_dir.is_dir()
    assert (top_dir / 'metadata.json').exists()
    assert (top_dir / 'merged_model.xml').exists()
    assert (field_dir / 'trial_data.csv').exists()

def test_no_overwrite():
    with pytest.raises(McsUserError, match="Directory '.*' already exists"):
        Simulation.new(sim_dir, [], analysis_name, trials,
                       overwrite=False, field_names=[field_name])

def test_load_simulation():
    sim = Simulation(sim_dir)
    assert sim.trials == trials
    assert sim.field_names == [field_name]

    field = sim.analysis.fields()[0]
    attr = sim.lookup("Analysis.GWP_horizon", field)
    assert attr.name == 'GWP_horizon' and attr.value.m == 100

    with pytest.raises(McsUserError, match="Simulation directory '.*' does not exist."):
        Simulation("/no/such/directory")

def test_distribution():
    Distribution.instances.clear()

    with pytest.raises(McsUserError, match="attribute name format is.*"):
        Distribution("foo.bar.baz", None)

    assert len(Distribution.instances) == 0

    # with pytest.raises(McsUserError, match="Simulation directory '.*' does not exist."):
