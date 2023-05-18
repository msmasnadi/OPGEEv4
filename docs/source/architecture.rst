Software Architecture
========================

.. note:: This file is under development.

Overview
----------

  * A framework for some of this is defined in :doc:`Tutorial_1 <tutorial_1>`. (Need to consolidate)

  * Modeling framework that builds a specific model specified in XML files

  * Designed to provide as much as possible built-in, while allowing user-defined customizations

  * XML template named "template" is defined in opgee.xml

    * Contains typical structure of a range of oil and gas production fields
    * Sets of related processes are defined in "process groups" which can be enabled or disabled together
    * Structure is determined by user-specified values of pre-defined "attributes" in XML

    * Fields can be defined by reference to a template
      * User can specify additions and deletions to Field definitions
      * User can specify values of attributes which control Field structure

  * Configuration file

    * Controls logging, inclusion of custom classes, stream components, and more

Plug-in architecture
----------------------

  * Built-in sub-commands (plug-ins internal to the ``opgee`` package)
  * User-defined plug-ins create additional sub-commands

XML processing
----------------

  * ``AttrDef``

    * Support for constraints on attribute values

  * ``Options, Option``
  * ``ClassAttrs``
  * ``ProcessGroup``
  * Analysis groups

Classes
----------
  * Major structural classes

    * ``Model, Analysis, Field, Process, Stream, Boundary, Energy, Emissions``
    * Petroleum and gas processing (subclasses of ``Process``)

  * Thermodynamics support:

    * ``Oil, Gas, Water, Dry Air, Wet Air, TemperaturePressure``

  * Monte Carlo simulation and SmartDefault support

    * ``Distribution, Simulation, SmartDefault``

  * Tabular data support

    * ``TableManager, Cell, TableUpdate``

  * Error classes

Management of tabular data
---------------------------

  * Caching of tabular data from CSVs

    * Support for different indices, column specifications, data type

    * TBD: support for user-provided tables

  * XML support for user-specified modifications to built-in tabular data

Assorted features
-------------------

  * Storage of intermediate values

    * Allows ``Process`` subclasses to share information

  * User-defined customizations

    * System boundaries
    * Additions to Stream components
    * Process subclasses

Running a Field
----------------

  * How the ``Model`` structure is assembled
  * How a ``Field`` is run

    * in MCS and standard modes

  * Handling of cyclic processing

    * User-defined maximum iterations and solution tolerance like in Excel

Fledgling Graphical User Interface
-----------------------------------

  * Network visualization
  * Attribute value examination / modification (incomplete)
  * Running a field and examining results

Test and documentation frameworks
------------------------------------

  * pytest
  * Travis CI (installs package and runs tests)
  * Codecov and Coveralls (reports on code coverage by tests)
  * ReadTheDocs (builds documentation at opgee.readthedocs.io)

