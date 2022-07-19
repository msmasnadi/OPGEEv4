from pathlib import Path
import pytest
from opgee.error import McsUserError
from opgee.mcs.simulation import read_distributions, Simulation, Distribution

field_name = 'gas_lifting_field'
analysis_name = 'test_analysis'
sim_dir = '/tmp/test-mcs'
N = 100

def test_missing_analysis():
    with pytest.raises(McsUserError, match="Analysis '.*' was not found"):
        Simulation.new(sim_dir, [], analysis_name + "_Not_A_Valid_Name_", N,
                       overwrite=True, field_names=[field_name])

def test_simulation():
    read_distributions(pathname=None)
    assert all([isinstance(d, Distribution) for d in Distribution.distributions()])

    # new(sim_dir, model_files, analysis_name, trials,
    #     field_names=None, overwrite=False, use_default_model=True)
    model_files = []
    Simulation.new(sim_dir, model_files, analysis_name, N,
                   overwrite=True, field_names=[field_name])

    top_dir = Path(sim_dir)
    field_dir = top_dir / field_name
    assert field_dir.is_dir()
    assert (top_dir / 'metadata.json').exists()
    assert (top_dir / 'merged_model.xml').exists()
    assert (field_dir / 'trial_data.csv').exists()

def test_no_overwrite():
    with pytest.raises(McsUserError, match="Directory '.*' already exists"):
        Simulation.new(sim_dir, [], analysis_name, N,
                       overwrite=False, field_names=[field_name])

def test_load_simulation():
    sim = Simulation(sim_dir)
    assert sim.trials == N
    assert sim.field_names == [field_name]

    with pytest.raises(McsUserError, match="Simulation directory '.*' does not exist."):
        Simulation("/no/such/directory")

def test_distribution():
    with pytest.raises(McsUserError, match="attribute name format is.*"):
        Distribution("foo.bar.baz", None)

