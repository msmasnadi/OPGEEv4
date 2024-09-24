Software Architecture
========================

.. note:: This file is under development.

Overview
----------

.. The following text appears in tutorial_1 as well. Probably better placed here.

OPGEE is designed as a generalized LCA / simulation framework to model the energy use by, and greenhouse
gas (GHG) emissions from, a set of processes linked by streams of substances, where each process
manipulates its input streams based on thermodynamic principles and/or regression
equations to produce one or more output streams. Groups of processes and streams are organized into
Fields, representing physical oil or gas fields and their materials and energy flows.

The model analyses a `functional unit` of 1 MJ of either gas or oil produced at a user-designated system
boundary of an oil or gas field. System boundaries are discussed further below. After a fields is run,
the carbon intensity (CI) of the functional unit is calculated and reported in units of
g CO\ :sub:`2`-eq MJ\ :sup:`-1`. See also: :doc:`calculation`.

OPGEE models are defined in :doc:`XML format <opgee-xml>`. OPGEE includes an XML input
file ``opgee.xml`` that provides a range of useful field configurations in a field template that
can be modified without re-stating entire field definition. Users can also specify in their
OPGEE configuration file (``opgee.cfg``) the locations of custom Python modules that implementing
a subclass of ``Process`` which can then be referenced from a user's XML files.
See also: :doc:`config`.

The field named "template" in ``opgee.xml`` contains:

    * Definitions for a range of oil and gas production fields
    * Sets of related processes are defined in "process groups" which can be enabled or
      disabled together based on user-specified values of pre-defined "attributes" in XML

    * Fields can be defined by reference to a template, specifying:

      * additions and deletions to Field definitions
      * attributes which control Field structure

System boundaries
~~~~~~~~~~~~~~~~~~

.. note:: Create a network graph showing different system boundaries

In OPGEE, the system boundary is defined by a subclass of ``Process`` which can have multiple input
and streams but performs no actual processing: it merely copies its inputs to its outputs based on
stream contents. A boundary process cannot be within a process cycle.

Three system boundaries are provided in the default model: `Production`, `Transportation`, and
`Distribution`. These differ only in whether the boundary is the point of storage of the product,
or whether it includes processes required for the transport or distribution of the product.
Boundaries are defined in the XML input files, allowing users to
define alternative boundaries if needed.

To compute CI, the total GWP-weighted greenhouse gas emissions from all processes is summed and
divided by the total flow of the designated product (oil or gas) through the chosen boundary
process.
See also: :doc:`opgee-xml` and :doc:`calculation`

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

See also: Class documentation for :py:class:`~opgee.emissions.Emissions` and
:py:class:`~opgee.energy.Energy`


Management of tabular data
---------------------------
OPGEE provides a system for accessing tabular data stored in CSV files. Data is loaded into
a pandas ``DataFrame`` on demand. CSV header format supports files with/without indices and
specification of data types. Built-in tabular data can be modified through XML statements.

See also: :doc:`opgee-xml` for documentation of the XML, and class documentation for
:py:class:`~opgee.table_manager.TableManager` and :py:class:`~opgee.table_update.TableUpdate`


Model Validation
-------------------
The major model-building classes -- ``Model``, ``Analysis``, ``Field``, ``Process``, and ``Stream`` -- inherit
the ``validate()`` method from ``Container``. After a model is loaded from XML, the ``ModelFile`` instance calls
``model.validate()``, which descends through the ``Model`` to ``Analysis`` instances, to ``Field`` and
``Process`` instances.

The ``Model`` and ``Analysis`` classes currently do not override the ``validate()`` method inherited from
``Container``, which merely calls ``validate()`` on the object's children. The children of ``Model`` are
``Analysis`` instances. The children of ``Analysis`` instances are ``Field`` instances.


The ``Field.validate()`` method ensures that the chosen system boundary process exists in the model,
that there are boundary processes defined, and that
boundary processes are not included in cycles, nor included in ``Aggregator`` instances that
includes processes on both sides of the boundary. It also checks that steam:oil ratio (``SOR``)
is not 0 for ``steam_flooding`` fields.


All ``Process`` subclasses calls two methods, ``validate_streams()`` and ``validate_proc``;
the prior checks that required input and output streams are present, while the latter is an
abstract method intended to be overridden as appropriate in each subclass of ``Process``.

The ``Process`` class defines two class variables, ``_required_inputs`` and ``_required_outputs``,
which can be set in each subclass to the names of stream *contents* expected to be defined by
input or output streams, accordingly.

XML processing
----------------

AttrDef
~~~~~~~~~~
The XML element ``<AttrDef>`` defines metadata for an attribute of an OPGEE XML element.
The information is stored in the class :py:class:`~opgee.attributes.AttrDef` when the
model is constructed.

Options
~~~~~~~~
The XML element ``<Options>`` defines a set of possible values for an attribute. This
is used for both validation and to generate the interactive user interface.

ProcessChoice and ProcessGroup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A ``<ProcessGroup>`` describes a set of ``<ProcessRef>`` and ``<StreamRef>`` elements that
can be enabled or disabled as a set. The ``<ProcessChoice>`` element encloses multiple
``<ProcessGroup>`` elements and selects among them based on the value of an attribute
named in the ``<ProcessChoice>``, whose value must match the name of one of the enclosed
``<ProcessGroup>`` elements.

All XML elements are described further in :doc:`opgee-xml`.


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

