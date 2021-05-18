import pytest
from opgee.error import CommandlineError
from opgee.windows import IsWindows

DEVNULL = 'nul' if IsWindows else '/dev/null'

@pytest.mark.parametrize(
    "args", [
        ['graph', '--classes', 'core', '--classes_output', DEVNULL],
        ['graph', '--field', 'test', '--field_output', DEVNULL],
        ['graph', '--hierarchy_output', DEVNULL],
    ]
)
def test_graphing(opgee, args):
    try:
        opgee.run(None, args)
        good = True
    except Exception:
        good = False

    assert good

def test_unknown_field(opgee):
    with pytest.raises(CommandlineError, match=r"Field name .* was not found in model"):
        opgee.run(None, ['graph', '--field', 'unknown-field'])
