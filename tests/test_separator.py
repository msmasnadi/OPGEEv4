import pytest
from .utils_for_tests import load_test_model


@pytest.fixture(scope="module")
def test_separator(configure_logging_for_tests):
    return load_test_model('test_separator.xml')


def test_run(test_separator):
    analysis = test_separator.get_analysis('test_separator')
    field = analysis.get_field('test')
    field.run(analysis, compute_ci=False)


def test_run_steam(test_separator):
    analysis = test_separator.get_analysis('test_separator')
    field = analysis.get_field('test')
    field.set_attr("steam_flooding", 1)
    field.run(analysis, compute_ci=False)


def test_run_heater(test_separator):
    analysis = test_separator.get_analysis('test_separator')
    field = analysis.get_field('test')
    field.set_attr("heater_treater", 1)
    field.run(analysis, compute_ci=False)

