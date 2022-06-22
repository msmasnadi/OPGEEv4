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

class PhonyAnalysis:
    def __init__(self, name):
        self.name = name
        self.attr_dict = dict()

def test_simulation():
    pathname = '/tmp/test-mcs'
    sim = Simulation.new(pathname, overwrite=True)
    N = 1000
    analysis  = PhonyAnalysis('random_name')
    attr_dict = {'WOR-MEAN': 10,
                 'WOR-SD': 2,
                 'TEST.age': 20,
                 'TEST.WOR-SD': 3,
                 'TEST.foo': 3,
                 'TEST.bar': 4,
                 }
    sim.generate(analysis, N, attr_dict)


def test_dependency_decorators():
    from opgee.mcs.LHS import getPercentiles

    attr_dict = {'TEST.foo': 3, 'TEST.bar': 4, 'TEST.baz': 10, 'TEST.age': 20}

    dep_obj = Dependency.find('Distribution', 'MyClass', 'TEST.WOR-SD')
    args = [attr_dict[attr_name] for attr_name in dep_obj.dependencies]
    rv = dep_obj.func(*args)

    N = 100
    values = rv.ppf(getPercentiles(N))

    assert len(values) == N

    objs = Distribution.distributions()

    # look only for our named attributes
    attr_names = ['TEST.foo', 'TEST.bar', 'TEST.age', 'TEST.abcdef', 'TEST.WOR-SD', 'TEST.WOR']
    assert [name for name in objs if name.startswith('TEST.')] == attr_names
