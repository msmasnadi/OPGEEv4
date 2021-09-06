# Create a registry of smart defaults
from opgee.error import OpgeeException

smart_default_registry = {}

def smart_default(attr_name):
    def decorator(func):
        def wrapped_func(*args, **kwargs):
            print(f'Calling smart default for attribute {attr_name} in class {class_name}')
            return func(*args, **kwargs)

        # func.__qualname__ is a string of format "class_name.func_name"
        class_name = func.__qualname__.split('.')[0]
        print(f'Saving smart default for attribute {attr_name} in class {class_name}')
        smart_default_registry[(class_name, attr_name)] = wrapped_func
        return wrapped_func
    return decorator

class MyClass:
    @smart_default('abcdef')
    def test(self):
        print(f"Called test({self})")

def set_smart_default(cls, attr_name):
    class_name = cls.__name__
    func = smart_default_registry.get((class_name, attr_name))
    if func:
        func(cls, attr_name)
    else:
        raise OpgeeException(f"There is no function registered to handle attribute {attr_name} for class {class_name}")

obj = MyClass()
obj.test()
pass
