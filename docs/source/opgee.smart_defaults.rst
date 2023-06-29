Smart Defaults
================

Smart defaults are functions whose return values depend on the values
of other model attributes. The ``SmartDefault`` class stores information
required to run a "smart default" function.

Since smart defaults depend on attributes which may themselves have smart defaults, the
functions must be evaluated in the correct order. A directed graph is created representing
the set of smart defaults and their dependencies. The graph is sorted topologically to
produce the proper run order. The functions are then invoked twice: first when the ``Field``
is instantiated from XML, since some attributes control the structure of the model, and
then again (only in Monte Carlo settings) after applying values from parameter distributions.

Smart default functions are defined using the ``@SmartDefault.register`` decorator:

.. code-block:: python

   @SmartDefault.register("Analysis.attr_name", ["dep1", "dep2"])
     def my_func(arg1, arg2)
       return do_something(arg1, arg1)

The arguments are the name of the attribute that is computed by the function,
and a list of attributes on which the function depends. The values of the attributes
are acquired from the corresponding object and passed to the function following the
decorator. In the example above, the values of "dep1" and "dep2" are passed to the
function ``my_func`` as arguments ``arg1`` and ``arg2``. The function should return
the value to set the named attribute to.

The names of the target attribute and the dependencies can be simple attribute names,
or a class or process name can be specified using dot notation, e.g., "Field.my_attribute"
to identify the location of the attribute.

If the class or process specifier is absent, the default attribute location differs
depending on whether the wrapped function is a method
or a regular function. If it is a method, a missing location specifier defaults to the
name of the class defining the method. If the wrapped function is a regular (non-method)
function, the location specifier defaults to "Field".

.. automodule:: opgee.smart_defaults
   :members:
