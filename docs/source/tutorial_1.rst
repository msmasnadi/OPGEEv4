OPGEE model structure
==========================

OPGEE is designed as a generalized LCA/simulation model of processes linked by streams
of substances, where each process consumes input streams based and processes them
based on thermodynamic principles and/or regression equations to produce one or more
output streams. OPGEE supports process cycles, where the output of process `A` is an
input to process `B` whose output ultimate flows back as an input to `A`, through zero
or more intermediate processes.

The energy consumed and greenhouse gas emissions produced by each process are tracked,
and the flow of the functional target (oil or gas) is tracked to one or more user-defined
system boundaries, allowing the calculation of a "carbon intensity" in units of
g CO\ :sub:`2`-eq MJ\ :sup:`-1`.

See also: :doc:`config`

OPGEE's Python classes
----------------------------

Model
^^^^^^^
The ``Model`` class is a container for one or more ``Analysis`` and ``Field`` elements,
representing a complete OPGEE model as described by one or more XML input files.

  * Class documentation for :class:`.Model`
  * XML documentation for the `<Model> <opgee-xml.html#model>`__ element

Analysis
^^^^^^^^^^

The ``Analysis`` class references one or more ``Field`` instances and stores a small
number of attributes that are shared across an analysis, namely:

  * GWP horizon -- either 20 or **100** years
  * GWP version -- one of AR4, **AR5**, AR5 with C-cycle feedback, or AR6
  * Functional unit -- either **oil** or gas

Default values are indicated in bold text.

A ``Field`` may appear in multiple Analyses, e.g., to run it with different
GWP time horizons or values from different IPCC reports.

  * Class documentation for :class:`.Analysis`
  * XML documentation for the `<Analysis> <opgee-xml.html#analysis>`__ element

Field
^^^^^^^

The ``Field`` is the primary unit of carbon intensity analysis. It is a
container for a directed graph of ``Process`` instances connected by ``Stream``
instances. A ``Field`` can have multiple ``Boundary`` nodes that identify
points at which CI and energy use can be calculated.

Most OPGEE attributes are defined at the ``Field`` level.

  * Class documentation for :class:`.Field`
  * XML documentation for the `<Field> <opgee-xml.html#field>`__ element

Process
^^^^^^^^^

The ``Process`` class is an abstract class, whose subclasses simulate the physical
processing units required by oil and gas fields. A ``Process`` can have multiple
inputs and outputs, represented by instances of the ``Stream`` class.

See :doc:`opgee.processes` for a comprehensive description of OPGEE's built-in
processes.

  * Class documentation for :class:`.Process`
  * XML documentation for the `<Process> <opgee-xml.html#process>`__ element


Stream
^^^^^^^^

The ``Stream`` class represents the substances the directed flow between two ``Process``
instances. Each ``Stream`` declares its contents so that processes can find specific
input and output streams based on what they carry.

  * Class documentation for :class:`.Stream`
  * XML documentation for the `<Stream> <opgee-xml.html#stream>`__ element


Attribute subsystem
----------------------------

Attribute
^^^^^^^^^^^

  * Class documentation for :class:`.A`
  * XML documentation for the `<A> <opgee-xml.html#a>`__ element

Attribute definition
^^^^^^^^^^^^^^^^^^^^^^

  * Class documentation for :class:`.AttrDef`
  * XML documentation for the `<AttrDef> <opgee-xml.html#attrdef>`__ element

Class attributes
^^^^^^^^^^^^^^^^^^^^^^

  * Class documentation for :class:`.ClassAttrs`
  * XML documentation for the `<ClassAttrs> <opgee-xml.html#classattrs>`__ element
