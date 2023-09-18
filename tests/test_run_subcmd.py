from contextlib import contextmanager
from glob import glob
import os
import pytest
from opgee.config import setParam, pathjoin
from opgee.error import CommandlineError
from opgee.tool import opg
from .utils_for_tests import path_to_test_file

@contextmanager
def tempdir():
    import tempfile
    import shutil

    d = tempfile.mkdtemp()
    try:
        yield d
    finally:
        shutil.rmtree(d)

def test_missing_output_dir(opgee_main):
    name = 'test'
    with pytest.raises(CommandlineError, match="Non-MCS runs must specify -o/--output-dir"):
        opgee_main.run(None, ['run', '-a', name])

def DEPRECATED_test_unknown_analysis(opgee_main):
    xml_path = path_to_test_file('test_run_subcmd.xml')
    name = 'unknown-analysis'

    with tempdir() as output_dir:
        args = ['run',
                '-m', xml_path,
                '-a', name,
                '--no-default-model',
                '--cluster-type=serial',
                '--output-dir', output_dir]

        with pytest.raises(CommandlineError, match=r"Specified analyses .* not found in model"):
            opgee_main.run(None, args)

def test_run_one_field(opgee_main):
    import pandas as pd

    xml_path = path_to_test_file('test_run_subcmd.xml')
    with tempdir() as output_dir:
        args = ['run',
                '-m', xml_path,
                '-a', 'test',
                '--no-default-model',
                '--cluster-type=serial',
                '--output-dir', output_dir]
        print("opg ", ' '.join(args))

        opgee_main.run(None, args)

        df = pd.read_csv(pathjoin(output_dir, 'carbon_intensity.csv'), index_col='node')

    assert df is not None and len(df) == 4
    assert df.loc['TOTAL', 'CI'] == 0.0


def test_unknown_field(opgee_main):
    name = 'unknown-field'
    xml_path = path_to_test_file('test_run_subcmd.xml')
    with tempdir() as output_dir:
        args = ['run',
                '-m', xml_path,
                '-f', name,
                '--no-default-model',
                '--cluster-type=serial',
                '--output-dir', output_dir]
        print("opg ", ' '.join(args))

    with pytest.raises(CommandlineError, match="Fields not found in .*"):
        opgee_main.run(None, args)


def test_field_or_analysis(opgee_main):
    xml_path = path_to_test_file('test_run_subcmd.xml')

    with tempdir() as output_dir:
        args = ['run',
                '-m', xml_path,
                '--output-dir', output_dir]
        print("opg ", ' '.join(args))

        # CommandlineError("Must indicate one or more fields or analyses to run")
        with pytest.raises(CommandlineError, match="Must indicate one or more fields or analyses to run"):
            opgee_main.run(None, args)

def test_missing_model_file(opgee_main):
    with tempdir() as output_dir:
        args = ["run", "--output-dir", output_dir, '--no-default-model', '-a', 'test']
        print("opg ", " ".join(args))

        # CommandlineError("No model to run: the --model-file option was not used and --no-default-model was specified.")
        with pytest.raises(CommandlineError, match="No model to run.*"):
            opgee_main.run(None, args)

def test_packetization(opgee_main):
    import pandas as pd

    xml_path = path_to_test_file('test-fields-10.xml')

    fields = 7
    batch_start = 2      # arbitrary start number for result batches
    packet_size = 3
    cluster_type = 'serial'
    # cluster_type = 'local'

    with tempdir() as output_dir:
        args = ['run',
                '-m', xml_path,
                '--output-dir', output_dir,
                '-a', 'test-fields',
                '--no-default-model',
                '--cluster-type', cluster_type,
                '--num-tasks=2',
                '--batch-size=1',       # save each packet in a separate CSV
                f'--num-fields={fields}',
                f'--packet-size={packet_size}',
                f'--batch-start={batch_start}',
                ]
        print("opg ", ' '.join(args))

        opgee_main.run(None, args)

        csv_files = glob(f"{output_dir}/*.csv")
        d = {os.path.basename(name): pd.read_csv(name) for name in csv_files}

    # Should find 3 result files; 2 with 3 results each, and one with 1 result.
    num_files = fields // packet_size + (1 if fields % packet_size else 0)
    assert len(d) == num_files
    expected = (f"carbon_intensity_{n}.csv" for n in
                range(batch_start, batch_start + num_files))
    assert set(expected) == set(d.keys())

    last_batch = batch_start + num_files - 1
    last_csv = f'carbon_intensity_{last_batch}.csv'
    last_df = d[last_csv]
    assert len(last_df.field.unique()) == 1
    del d[last_csv]
    for name, df in d.items():
        assert len(df.field.unique()) == packet_size

def test_run_test_model(opgee_main):
    setParam('OPGEE.ClassPath', path_to_test_file('user_processes.py'))

    xml_path = path_to_test_file('test_model2.xml')
    cmd = f"run -f Field1 -m {xml_path} --no-default-model"
    print(f"Running 'opg {cmd}'")

    try:
        opg(cmd)
        good = True

    except Exception as e:
        print(f"ERROR: test_run_test_model: {e}")
        good = False

    setParam('OPGEE.ClassPath', '')  # avoid reloading user_processes.py
    assert good
