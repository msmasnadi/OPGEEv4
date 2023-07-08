Attributes
===========

In OPGEE the term "attributes" refers to a class of model parameters that are pre-defined
with metadata (attribute definitions) and are class-specific, i.e., they related to
Analysis, Field, Process, or subclasses of Process.

Attributes are central to the operation of both the "Smart Defaults" and Monte Carlo
simulation (MCS) subsystems. This page provides a brief overview of how attributes are
used in these subsystems. See the pages linked below for more information.

See :obj:`opgee.attributes` for the Python API and more detailed documentation.

Attribute Definitions
----------------------

Attributes used in model description XML files must be defined in attributes.xml.
Attempts to use undefined attributes results in a runtime exception.

Attributes are defined in `{opgee}/etc/attributes.xml <opgee-xml.html#attributes-xml>`__
using the ``<AttrDefs>`` element. Definitions include the attribute type (text string,
integer, floating point number, or one of defined set of choices, as well as default
values and other metadata.

Simple Defaults
-----------------
Attributes defined in `{opgee}/etc/attributes.xml <opgee-xml.html#attributes-xml>`__
are set to their default value if a value is not provided explicitly in a model
description XML file. Default values can be overridden in an MCS if a distribution
is defined for the attribute. Explicitly set values are not replaced in an MCS.

Smart Defaults
---------------
:doc:`opgee.smart_defaults` are functions that set the value of an attribute based
on calculations using the values of other model attributes.
The :class:`.SmartDefault` class stores information
required to run a "smart default" function. Most Smart Defaults are defined in the
:class:`.Field` class. See :doc:`opgee.smart_defaults` for more information.

Monte Carlo Simulation
------------------------

OPGEE's :doc:`monte-carlo` framework defines probability distributions for values
of specific attributes. If the attribute value has been set explicitly in the
model XML, the distribution is *not* applied. See :doc:`monte-carlo` for more
information.
