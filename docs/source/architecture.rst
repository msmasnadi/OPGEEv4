Software Architecture
========================

.. note:: This file is under development.

Overview
----------

.. The following text appears in tutorial_1 as well. Probably better placed here.

OPGEE is designed as a generalized LCA / simulation model of processes linked by streams of substances,
where each process manipulates some input streams based on thermodynamic principles and/or regression
equations to produce one or more output streams. Groups of processes and streams are organized into
fields, representing physical oil or gas fields and their flow of materials and energy through the
various processing units to the field boundary.

The model analyses a functional unit of 1 MJ of either gas or oil produced at a user-designated system
boundary of an oil or gas field. System boundaries are discussed further below. After a fields is run,
the carbon intensity (CI) of the functional unit is calculated and reported in units of
g CO\ :sub:`2`-eq MJ\ :sup:`-1`. (See :doc:`calculation` for more information.)

System boundaries
~~~~~~~~~~~~~~~~~~

In OPGEE, the system boundary is defined by a subclass of ``Process`` which can have multiple input
and streams but performs no actual processing: it merely copies its inputs to its outputs based on
stream contents. A boundary process cannot be within a process cycle.

Three system boundaries are provided in the default model: "Production", "Transportation", and
"Distribution". These differ only in whether the boundary is the point of storage of the product,
or whether it includes processes required for the transport or distribution of the product.
Boundaries are defined in the XML input files, allowing users to
define alternative boundaries if needed.

To compute CI, the total GWP-weighted greenhouse gas emissions from all processes is summed and
divided by the total flow of the designated product (oil or gas) through the chosen boundary
process.

.. note:: Create a network graph showing different system boundaries

Process cycles
~~~~~~~~~~~~~~~~~
Oil and gas fields typically contain process cycles,
in which the output of process A is an input to process B, whose output ultimate flows back as an input
to A, through zero or more intermediate processes. OPGEE handles process cycles iteratively, running
until (i) convergence, i.e., the change from one iteration to the next of a designated variable is
below a user-defined threshold, or (ii) the user-defined maximum number of iterations has run without
convergence, at which point the run terminates with an error.

Energy and emissions
~~~~~~~~~~~~~~~~~~~~~~

The energy consumed and greenhouse gas emissions produced by each process are tracked, and the flow
of the functional target (oil or gas) is tracked to one or more user-defined system boundaries,
allowing the calculation of a carbon intensity in units of g CO\ :sub:`2`-eq MJ\ :sup:`-1`.

.. seealso:: Class documentation for :py:class:`~opgee.emissions` and :py:class:`~opgee.energy`

To Do
~~~~~~~

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

XML processing
----------------

  * ``AttrDef``

    * Support for constraints on attribute values

  * ``Options, Option``
  * ``ClassAttrs``
  * ``ProcessGroup``
  * Analysis groups

.. Maybe this should exist only in the API section. Here, focus on structure.

Classes
----------
  * Major structural classes

    * ``Model, Analysis, Field, Process, Stream, Boundary, Energy, Emissions``
    * Petroleum and gas processing (subclasses of ``Process``)

  * Thermodynamics support:

    * ``Oil, Gas, Water, Dry Air, Wet Air, TemperaturePressure``

  * Monte Carlo simulation

    * :doc:`monte-carlo`
    * ``Distribution, Simulation, SmartDefault``

  * SmartDefault support

    * :doc:`opgee.smart_defaults`

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


Command-line interface
------------------------

Plug-in architecture
~~~~~~~~~~~~~~~~~~~~~~

  * Built-in sub-commands (plug-ins internal to the ``opgee`` package)
  * User-defined plug-ins create additional sub-commands


Graphical User Interface
------------------------------

  * Network visualization
  * Attribute value examination / modification (incomplete)
  * Running a field and examining results


Test and documentation frameworks
------------------------------------

  * pytest
  * Travis CI (installs package and runs tests)
  * Codecov and Coveralls (reports on code coverage by tests)
  * ReadTheDocs (builds documentation at opgee.readthedocs.io)

