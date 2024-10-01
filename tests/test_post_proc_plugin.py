import os
import pytest

from opgee.analysis import Analysis
from opgee.constants import DETAILED_RESULT
from opgee.error import AbstractMethodError, McsUserError
from opgee.field import Field, FieldResult
from opgee.post_processor import PostProcessor

from .utils_for_tests import load_test_model, path_to_test_file, tempdir

@pytest.fixture(scope="function")
def test_model2(configure_logging_for_tests):
    # This fixture also serves to test user classpath
    model = load_test_model('test_model2.xml', class_path=path_to_test_file('user_processes.py'))
    return model

def test_simple_post_processor(test_model2):
    analysis = test_model2.get_analysis('Analysis1')
    field = test_model2.get_field('Field1')
    result = FieldResult(analysis.name, field.name, DETAILED_RESULT)

    PostProcessor.decache()

    path = path_to_test_file('simple_post_processor.py')
    plugin = PostProcessor.load_plugin(path)

    PostProcessor.run_post_processors(analysis, field, result)

    assert len(plugin.results) == 1

    pair = plugin.results[0]
    assert pair[0] == 'dummy-data' and pair[1] == result

    output_dir = os.path.dirname(path)
    PostProcessor.save_post_processor_results(output_dir)

    csv_file = os.path.join(output_dir, 'simple_post_processor.csv')
    assert os.path.exists(csv_file)
    os.remove(csv_file)

    # prior results are cleared after saving
    assert len(plugin.results) == 0


class InvalidPostProcessor(PostProcessor):
    # Doesn't define required run() method
    pass

def test_invalid_post_processor(test_model2):
    analysis = test_model2.get_analysis('Analysis1')
    field = test_model2.get_field('Field1')
    result = FieldResult(analysis.name, field.name, DETAILED_RESULT)

    # class is missing run() method
    instance = InvalidPostProcessor()

    with pytest.raises(AbstractMethodError):
        instance.run(analysis, field, result)

def test_missing_plugin():
    path = path_to_test_file('MISSING-FILE.py')

    with pytest.raises(McsUserError, match=r"Path to plugin '.*' does not exist"):
        PostProcessor.load_plugin(path)

def test_missing_subclass():
    path = path_to_test_file('broken_post_proc_plugin.py')

    with pytest.raises(McsUserError, match=r'No subclass of PostProcessor .*'):
        PostProcessor.load_plugin(path)

def test_cmd_line_post_proc(opgee_main):
    PostProcessor.decache()
    plugin_path = path_to_test_file('simple_post_processor.py')
    xml_path = path_to_test_file('test_run_subcmd.xml')

    with tempdir() as output_dir:
        args = [
            'run',
            '-m', xml_path,
            '-a', 'test',
            '--no-default-model',
            '--cluster-type=serial',
            '--output-dir', output_dir,
            '--post-plugin', plugin_path,
        ]
        print("opg ", ' '.join(args))

        opgee_main.run(None, args)

        inst = PostProcessor.instances
        assert len(inst) == 1
        assert inst[0].__class__.__name__ == 'SimplePostProcessor'

        csv_file = os.path.join(output_dir, 'simple_post_processor.csv')
        assert os.path.exists(csv_file)
