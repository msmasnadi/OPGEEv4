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


def test_run(test_oil_branch):
    analysis = test_oil_branch.get_analysis('test_oil_branch')
    field = analysis.get_field('oil_stabilization')
    field.run(analysis)


def test_run(test_oil_branch):
    analysis = test_oil_branch.get_analysis('test_oil_branch')
    field = analysis.get_field('heavy_oil_upgrading')
    field.set_attr("API", 8.6)
    field.set_attr("crude_oil_dewatering_output", "HeavyOilUpgrading")
    field.set_attr("upgrader_type", "Delayed coking")
    field.run(analysis)
#
#
# def test_run_heater(test_oil_branch):
#     analysis = test_oil_branch.get_analysis('test_oil_branch')
#     field = analysis.get_field('test')
#     field.set_attr("heater_treater", 1)
#     field.run(analysis)

