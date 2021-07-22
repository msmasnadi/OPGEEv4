import pytest
from opgee import Process
from .utils_for_tests import load_test_model


class Before(Process):
    def run(self, analysis):
        pass


class After(Process):
    def run(self, analysis):
        pass


@pytest.fixture(scope="module")
def test_oil_branch(configure_logging_for_tests):
    return load_test_model('test_oil_branch.xml')


def test_run_stab(test_oil_branch):
    analysis = test_oil_branch.get_analysis('test_oil_branch')
    field = analysis.get_field('oil_stabilization')
    field.run(analysis)


def test_run_upgrading(test_oil_branch):
    analysis = test_oil_branch.get_analysis('test_oil_branch')
    field = analysis.get_field('heavy_oil_upgrading')
    field.run(analysis)


def test_run_dilution(test_oil_branch):
    analysis = test_oil_branch.get_analysis('test_oil_branch')
    field = analysis.get_field('heavy_oil_diluent')
    field.run(analysis)


def test_run_bitumen(test_oil_branch):
    analysis = test_oil_branch.get_analysis('test_oil_branch')
    field = analysis.get_field('bitumen_dilution')
    field.run(analysis)
