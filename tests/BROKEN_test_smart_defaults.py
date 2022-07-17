from opgee.analysis import Analysis
from opgee.core import A
from opgee.field import Field
from opgee.mcs.simulation import Simulation
from opgee.smart_defaults import SmartDefault
from opgee.mcs.simulation import Distribution

@SmartDefault.register('TEST_abcdef', ['TEST_foo', 'TEST_bar'])
def smart_dflt_1(foo, bar):
    print(f"Called test_smart_dflt(foo:{foo} bar:{bar})")
    return 10000

class MyAnalysis(Analysis):
    def __init__(self, name):
        field_name = 'TestField'
        super().__init__(name, attr_dict={}, field_names=[field_name], groups=[])

        attrs = [
            A('TEST_WOR-MEAN', value=10, pytype=int, unit='fraction', explicit=False),
            A('TEST_WOR-SD', value=2, pytype=int, unit='fraction'),
            A('Field.age', value=20, pytype=int, unit='year'),
            A('TEST_foo', value=3, pytype=int, unit='tonne'),
            A('TEST_bar', value=4, pytype=int, unit='meter'),
        ]
        attr_dict = {attr.name: attr for attr in attrs}
        f = Field(field_name, attr_dict=attr_dict, streams=[], procs=[])
        self.field_dict = {field_name: f}

def test_simulation():
    analysis_name = 'random_name'
    #analysis = MyAnalysis(analysis_name)

    N = 1000
    pathname = '/tmp/test-mcs'
    Simulation.new(pathname, analysis_name=analysis_name, trials=N, overwrite=True)

def test_dependency_decorators():
    from opgee.mcs.LHS import getPercentiles

    attr_dict = {'TEST_foo': 3, 'TEST_bar': 4, 'TEST_baz': 10, 'TEST_age': 20}

    dep_obj = SmartDefault.find('Distribution', 'TEST_WOR-SD')
    args = [attr_dict[attr_name] for attr_name in dep_obj.dependencies]
    rv = dep_obj.func(*args)

    N = 100
    values = rv.ppf(getPercentiles(N))

    assert len(values) == N

    objs = Distribution.distributions()

    # look only for our named attributes
    attr_names = ['TEST_WOR-SD', 'TEST_WOR']
    assert [obj.attr_name for obj in objs if obj.attr_name.startswith('TEST_')] == attr_names
