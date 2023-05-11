from pathlib import Path
import pytest
from io import StringIO

from opgee.error import McsUserError
from opgee.mcs.simulation import read_distributions, Simulation, Distribution
from opgee.tool import opg

from .utils_for_tests import tmpdir, path_to_test_file

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

    field = sim.analysis.fields()[0]
    attr = sim.lookup("Analysis.GWP_horizon", field)
    assert attr.name == 'GWP_horizon' and attr.value.m == 100

def test_no_overwrite():
    with pytest.raises(McsUserError, match="Directory '.*' already exists"):
        Simulation.new(sim_dir, [], analysis_name, trials,
                       overwrite=False, field_names=[field_name])

def test_load_simulation():
    sim = Simulation(sim_dir)
    assert sim.trials == trials
    assert sim.field_names == [field_name]

    with pytest.raises(McsUserError, match="Simulation directory '.*' does not exist."):
        Simulation("/no/such/directory")

def test_distribution():
    Distribution.instances.clear()

    with pytest.raises(McsUserError, match="attribute name format is.*"):
        Distribution("foo.bar.baz", None)

    assert len(Distribution.instances) == 0

    # with pytest.raises(McsUserError, match="Simulation directory '.*' does not exist."):
