# Create a registry of smart defaults
from opgee.core import OpgeeObject
#from opgee.error import OpgeeException


class Dependency(OpgeeObject):
    # Registry is a dict keyed by tuple of (subclass, class_name, attr_name)
    # where 'subclass' is the class of the instance, which must be a subclass of
    # 'Dependency'.
    registry = {}

    def __init__(self, func_class, func_name, func, attr_name, dependencies):
        self.func_class = func_class    # the class containing func
        self.func_name  = func_name
        self.func = func
        self.attr_name = attr_name
        self.dependencies = dependencies
        self.subclass = subclass = type(self)

        print(f'Saving {subclass.__name__} for attribute {attr_name} in class {func_class}')
        # TBD: need to handle subclasses of Process?
        self.registry[(subclass, func_class, attr_name)] = self

    # The decorator function, i.e.,
    # @SmartDefault.register("attr_name", ["dep1", "dep2", ...])
    # def my_func() ...
    #
    @classmethod
    def register(cls, attr_name, dependencies):
        def decorator(user_func):
            # func.__qualname__ is a string of format "func_class.func_name"
            qualname = user_func.__qualname__
            func_class, func_name = qualname.split('.')

            def wrapped_func(*args):
                print(f'Calling {qualname} for attribute {attr_name} with dependencies {dependencies}')
                return user_func(*args)

            cls(func_class, func_name, wrapped_func, attr_name, dependencies)
            return wrapped_func

        return decorator


class SmartDefault(Dependency):
    # TBD: something like this
    def set_value(self, obj, attr_dict):
        values = [attr_dict[attr_name] for attr_name in self.dependencies]
        result = self.func(obj, *values)
        attr_dict[self.attr_name] = result
        return result


# TBD: these might fold into one class or most of the
#      functionality might migrate to superclass.
class Distribution(Dependency):
    # TBD: something like this
    def set_value(self, obj, attr_dict):
        values = [attr_dict[attr_name] for attr_name in self.dependencies]
        result = self.func(obj, *values)
        attr_dict[self.attr_name] = result
        return result

# # Decorator
# # TBD: may make this a classmethod of SmartDefault, e.g., @SmartDefault.register(...)
# def smart_default(attr_name, dependencies):
#     def decorator(func):
#         def wrapped_func(*args):
#             print(f'Calling smart default for attribute {attr_name} in class {class_name}')
#             return func(*args)
#
#         # func.__qualname__ is a string of format "class_name.func_name"
#         class_name = func.__qualname__.split('.')[0]
#         SmartDefault.registry[(class_name, attr_name)] = (wrapped_func, dependencies)
#         return wrapped_func
#     return decorator

class MyClass:
    @SmartDefault.register('abcdef', ['foo', 'bar'])
    def test_smart_dflt(self, foo, bar):
        print(f"Called test_smart_dflt({self}, foo:{foo} bar:{bar})")
        return 10000

    @Distribution.register('WOR-SD', ['age'])
    def test_dep(self, age):
        print(f"Called test_dep({self}, age:{age})")
        return 1000


# def set_smart_default(cls, attr_name):
#     class_name = cls.__name__
#     func = smart_default_registry.get((class_name, attr_name))
#     if func:
#         func(cls, attr_name)
#     else:
#         raise OpgeeException(f"There is no function registered to handle attribute {attr_name} for class {class_name}")

attr_dict = {'foo': 3, 'bar': 4, 'baz': 10, 'age': 20}

obj = MyClass()

wor_sd = Dependency.registry[(Distribution, 'MyClass', 'WOR-SD')]
wor_sd.set_value(obj, attr_dict)
pass
