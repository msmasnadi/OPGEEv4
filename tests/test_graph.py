import os

import pytest

from opgee.config import IsWindows
from opgee.error import CommandlineError
from tests.utils_for_tests import path_to_test_file

DEVNULL = 'nul' if IsWindows else '/dev/null'

is_sherlock = os.environ.get('LMOD_SYSHOST') == 'sherlock'
xml_path = path_to_test_file('gas_lifting_field.xml')

@pytest.mark.skipif(is_sherlock, reason="requires the graphviz/dot which isn't working on sherlock")
@pytest.mark.parametrize(
    "args", [
        ['graph', '--classes', 'core', '--classes-output', DEVNULL],
        ['graph', '--field', 'gas_lifting_field', '-x', xml_path, '--field-output', DEVNULL],
        ['graph', '--hierarchy-output', DEVNULL],
    ]
)
def test_graphing(opgee_main, args):
    try:
        opgee_main.run(None, args)
        good = True
    except Exception as e:
        import pdb; pdb.set_trace()
        # print(e)
        good = False

    assert good

@pytest.mark.skipif(is_sherlock, reason="requires the graphviz/dot which isn't working on sherlock")
def test_unknown_field(opgee_main):
    with pytest.raises(CommandlineError, match=r"Field name .* was not found in model"):
        opgee_main.run(None, ['graph', '--field', 'unknown-field'])
