OPGEE model structure
==========================

OPGEE is designed as a generalized LCA/simulation model of processes linked by streams
of substances, where each process processes some input streams based on thermodynamic
principles and/or regression equations to produce one or more output streams. Process
cycles, where the output of process `A` is an input to process `B` whose output ultimate
flows back as an input to `A`, through zero or more intermediate processes.

The energy consumed and greenhouse gas emissions produced by each process are tracked,
and the flow of the functional target (oil or gas) is tracked to one or more user-defined
system boundaries, allowing the calculation of a "carbon intensity" in units of
g CO\ :sub:`2`-eq MJ\ :sup:`-1`.

This page describes:

  * Python classes of the OPGEE model

  * Handling of process cycles

See also: :doc:`config`




OPGEE's Python classes
----------------------------

Analysis
^^^^^^^^^^

See also: :obj:`opgee.analysis.Analysis`

Field
^^^^^^^

See also: :obj:`opgee.field.Field`


Process
^^^^^^^^^

See also: :obj:`opgee.process.Process`


Stream
^^^^^^^^

See also: :obj:`opgee.stream.Stream`


Attribute subsystem
----------------------------

Attribute
^^^^^^^^^^^

See also: :obj:`opgee.core.A`


Attribute definition
^^^^^^^^^^^^^^^^^^^^^^

See also: :obj:`opgee.attributes.AttrDef`


Class attributes
^^^^^^^^^^^^^^^^^^^^^^

See also: :obj:`opgee.attributes.ClassAttrs`




-----------------------------------------------------

Process cycles
----------------

TBD

