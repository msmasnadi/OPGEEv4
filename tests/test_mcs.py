from pathlib import Path
#import pytest
from opgee.mcs.simulation import read_distributions, Simulation, Distribution

def test_simulation():
    read_distributions(pathname=None)
    assert all([isinstance(d, Distribution) for d in Distribution.distributions()])

    field_name = 'gas_lifting_field'
    analysis_name = 'test_analysis'
    N = 100
    pathname = '/tmp/test-mcs'
    # new(sim_dir, model_files, analysis_name, trials,
    #     field_names=None, overwrite=False, use_default_model=True)
    model_files = []
    Simulation.new(pathname, model_files, analysis_name, N,
                   overwrite=True, field_names=[field_name])

    top_dir = Path(pathname)
    field_dir = top_dir / field_name
    assert field_dir.is_dir()
    assert (top_dir / 'metadata.json').exists()
    assert (top_dir / 'merged_model.xml').exists()
    assert (field_dir / 'trial_data.csv').exists()

