from opgee.smart_defaults import Dependency, SmartDefault, Distribution

class MyClass:
    @SmartDefault.register('Field.abcdef', ['Field.foo', 'Analysis.bar'])
    def test_smart_dflt(self, foo, bar):
        print(f"Called test_smart_dflt({self}, foo:{foo} bar:{bar})")
        return 10000

    @Distribution.register('Field.WOR-SD', ['Field.age'])
    def test_dep(self, age):
        print(f"Called test_dep({self}, age:{age})")
        return 1000

    @Distribution.register('Field.WOR', ['Field.age', 'Field.WOR-SD'])
    def test_wor(self, age, wor_sd):
        print(f"Called test_wor({self}, age:{age}, wor_sd:{wor_sd})")
        return 1000

attr_dict = {'Field.foo': 3, 'Analysis.bar': 4, 'Field.baz': 10, 'Field.age': 20}

obj = MyClass()

dep_obj = Dependency.find('Distribution', 'MyClass', 'Field.WOR-SD')
dep_obj.set_value(obj, attr_dict)
run_order = list(Dependency.run_order())
pass
