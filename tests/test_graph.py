import pytest
from opgee.error import CommandlineError
from opgee.config import IsWindows

DEVNULL = 'nul' if IsWindows else '/dev/null'


@pytest.mark.parametrize(
    "args", [
        ['graph', '--classes', 'core', '--classes-output', DEVNULL],
        ['graph', '--field', 'test_gas_path_2', '--field-output', DEVNULL],
        ['graph', '--hierarchy-output', DEVNULL],
    ]
)
def test_graphing(opgee, args):
    try:
        opgee.run(None, args)
        good = True
    except Exception as e:
        print(e)
        good = False

    assert good


def test_unknown_field(opgee):
    with pytest.raises(CommandlineError, match=r"Field name .* was not found in model"):
        opgee.run(None, ['graph', '--field', 'unknown-field'])
