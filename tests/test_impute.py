import pytest
from opgee.error import OpgeeException
from opgee.process import Process
from .utils_for_tests import load_test_model
from opgee import ureg

class CopyingProcess(Process):
    def run(self, analysis):
        pass

    def impute(self):
        input = self.inputs[0] if self.inputs else None
        output = self.outputs[0] if self.outputs else None

        if input and output:
            input.temperature = output.temperature
            input.pressure = output.pressure

class Impute1(CopyingProcess): pass
class Impute2(CopyingProcess): pass
class Impute3(CopyingProcess): pass
class Impute4(CopyingProcess): pass

@pytest.fixture(scope="module")
def good_model(configure_logging_for_tests):
    return load_test_model('test_impute_model_good.xml')

@pytest.fixture(scope="module")
def bad_model(configure_logging_for_tests):
    return load_test_model('test_impute_model_bad.xml')


def test_impute_cycle_good(good_model):
    model = good_model
    model.validate()
    analysis = model.get_analysis('test')
    field = analysis.get_field('test')
    field._impute()

    stream = field.find_stream('Impute1 => Impute2')
    assert stream.pressure == ureg.Quantity(150.0, 'psia') and stream.temperature == ureg.Quantity(90.0, "degF")

def test_impute_cycle_bad(bad_model):
    model = bad_model
    model.validate()
    analysis = model.get_analysis('test')
    field = analysis.get_field('test')

    with pytest.raises(OpgeeException, match=r"Impute failed.*"):
        field._impute()

