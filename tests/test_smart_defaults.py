from opgee.smart_defaults import Dependency, SmartDefault, Distribution

class MyClass:
    @SmartDefault.register('TEST.abcdef', ['TEST.foo', 'TEST.bar'])
    def test_smart_dflt(self, foo, bar):
        print(f"Called test_smart_dflt({self}, foo:{foo} bar:{bar})")
        return 10000

    @Distribution.register('TEST.WOR-SD', ['TEST.age'])
    def test_dep(self, age):
        print(f"Called test_dep({self}, age:{age})")
        return 1000

    @Distribution.register('TEST.WOR', ['TEST.age', 'TEST.WOR-SD'])
    def test_wor(self, age, wor_sd):
        print(f"Called test_wor({self}, age:{age}, wor_sd:{wor_sd})")
        return 1000

def test_dependency_decorators():
    attr_dict = {'TEST.foo': 3, 'TEST.bar': 4, 'TEST.baz': 10, 'TEST.age': 20}

    obj = MyClass()

    dep_obj = Dependency.find('Distribution', 'MyClass', 'TEST.WOR-SD')
    dep_obj.set_value(obj, attr_dict)
    run_order = list(Dependency.run_order())

    # look only for our named attributes
    attr_names = ['TEST.foo', 'TEST.bar', 'TEST.age', 'TEST.abcdef', 'TEST.WOR-SD', 'TEST.WOR']
    assert [name for name in run_order if name.startswith('TEST.')] == attr_names
