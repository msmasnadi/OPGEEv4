from opgee.analysis import Analysis
from opgee.core import A
from opgee.field import Field
from opgee.smart_defaults import Dependency
from opgee.mcs.simulation import Simulation
from opgee.smart_defaults import SmartDefault
from opgee.mcs.simulation import Distribution
from opgee.mcs.distro import get_frozen_rv

@SmartDefault.register('TEST.abcdef', ['TEST.foo', 'TEST.bar'])
def smart_dflt_1(foo, bar):
    print(f"Called test_smart_dflt(foo:{foo} bar:{bar})")
    return 10000

@Distribution.register('TEST.WOR-SD', ['TEST.age'])
def age_distro(age):
    print(f"Called test_dep(age:{age})")
    return get_frozen_rv('normal', mean=age, stdev=age/4)

@Distribution.register('TEST.WOR', ['TEST.age', 'TEST.WOR-SD'])
def wor_distro(age, wor_sd):
    print(f"Called test_wor(age:{age}, wor_sd:{wor_sd})")
    return get_frozen_rv('normal', mean=age, stdev=wor_sd)

class MyAnalysis(Analysis):
    def __init__(self, name):
        field_name = 'TestField'
        super().__init__(name, attr_dict={}, field_names=[field_name], groups=[])

        attrs = [
            A('WOR-MEAN', value=10, pytype=int, unit='fraction', explicit=False),
            A('WOR-SD', value=2, pytype=int, unit='fraction'),
            A('TEST.age', value=20, pytype=int, unit='year'),
            A('TEST.WOR', value=3, pytype=int, unit='fraction'),
            A('TEST.WOR-SD', value=3, pytype=int, unit='fraction'),
            A('TEST.foo', value=3, pytype=int, unit='tonne'),
            A('TEST.bar', value=4, pytype=int, unit='meter'),
        ]
        attr_dict = {attr.name: attr for attr in attrs}
        f = Field(field_name, attr_dict=attr_dict, streams=[], procs=[])
        self.field_dict = {field_name: f}

def test_simulation():
    analysis_name = 'random_name'
    analysis = MyAnalysis(analysis_name)

    N = 1000
    pathname = '/tmp/test-mcs'
    sim = Simulation.new(pathname, analysis_name=analysis_name, trials=N, overwrite=True)

def test_dependency_decorators():
    from opgee.mcs.LHS import getPercentiles

    attr_dict = {'TEST.foo': 3, 'TEST.bar': 4, 'TEST.baz': 10, 'TEST.age': 20}

    dep_obj = Dependency.find('Distribution', 'TEST.WOR-SD')
    args = [attr_dict[attr_name] for attr_name in dep_obj.dependencies]
    rv = dep_obj.func(*args)

    N = 100
    values = rv.ppf(getPercentiles(N))

    assert len(values) == N

    objs = Distribution.distributions()

    # look only for our named attributes
    attr_names = ['TEST.WOR-SD', 'TEST.WOR']
    assert [obj.attr_name for obj in objs if obj.attr_name.startswith('TEST.')] == attr_names
