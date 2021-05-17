XML File Format
====================

The `opgee` package includes two XML files:

* `opgee/etc/opgee.xml` describes the default model, and

* `opgee/etc/attributes.xml` describes attributes of various model components.

Users can provide their own XML files which can be added to or used in place of,
the built-in definitions. The elements of the two files are described below,
followed by the contents of the files.


opgee.xml
------------

The elements that comprise the ``opgee.xml`` file are described below.

<Model>
^^^^^^^^^^

The top-most element, ``<Model>``, encloses one or more ``<Analysis>`` and
elements. The ``<Model>`` element takes the following attributes:

.. list-table:: <Model> Attributes
   :widths: 10 10 10 10
   :header-rows: 1

   * - Attribute
     - Required
     - Default
     - Values
   * - class
     - yes
     - (none)
     - text
   * - delete
     - no
     - "0"
     - boolean

The ``class`` attribute provides the name of an OPGEE class.

The ``delete`` attribute is used only by user-defined files. If the value
of the attribute is "1", "yes", or "true" (case insensitive), and a corresponding
value exists in the built-in XML structure, the built-in element and all elements
below it in the hierarchy are deleted before the new element is added.

<A>
^^^^^^^^^^^^^^^

The ``<A>`` element is used to set values for attributes of a model element. The XML schema allows model elements to
have zero or more attributes. The XML schema ensures that the ``<A>`` elements are syntactically correct. The semantics
of these elements is defined by a corresponding ``<AttrDef>`` element (see attributes.xml) in the named class. For example,

.. code-block:: xml

    <Process class="SurveyShip">
        <A name="weight">124</A>
        <A name="distance">2342</A>
    </Process >

provides values for two attributes, `weight` and `distance`, for the `SurveyVehicle` class. These have a
corresponding ``<AttrDef>`` definition in attributes.xml that provides the units, description, type, and
default value:

.. code-block:: xml

    <ClassAttrs name="SurveyShip">
        <AttrDef name="distance" type="float" desc="Distance of travel for survey" unit="mi">10000</Attr>
        <AttrDef name="weight" type="float" desc="Weight of ocean survey vehicle" unit="tons">100</Attr>
    </ClassAttrs>


The ``<A>`` element contains no further elements, but it contains an optional value for the attribute,
which if absent is assigned the default for this attribute. The `name` attribute must refer to
the name of an ``<AttrDef>`` defined in the built-in `attributes.xml` or a file loaded by
the user.

.. list-table:: <A> Attributes
   :widths: 10 10 10 10
   :header-rows: 1

   * - Attribute
     - Required
     - Default
     - Values
   * - name
     - yes
     - (none)
     - text

<Analysis>
^^^^^^^^^^^^^
This element contains one or more ``<Field>`` elements and accepts one required attribute, `name`.

.. list-table:: <Analysis> Attributes
   :widths: 10 10 10 10
   :header-rows: 1

   * - Attribute
     - Required
     - Default
     - Values
   * - name
     - yes
     - (none)
     - text

<Field>
^^^^^^^^^^
This element contains more or more ``<Aggregator>``, ``<Process>``, or ``<Stream>`` elements.

.. list-table:: <Field> Attributes
   :widths: 10 10 10 10
   :header-rows: 1

   * - Attribute
     - Required
     - Default
     - Values
   * - name
     - yes
     - (none)
     - text
   * - enabled
     - no
     - "1"
     - boolean
   * - extend
     - no
     - "0"
     - boolean

<Aggregator>
^^^^^^^^^^^^^^^
This element contains one or more ``<Aggregator>``, ``<Process>``, or ``<A>`` elements.

.. list-table:: <Aggregator> Attributes
   :widths: 10 10 10 10
   :header-rows: 1

   * - Attribute
     - Required
     - Default
     - Values
   * - name
     - yes
     - (none)
     - text
   * - enabled
     - no
     - "1"
     - boolean

<Process>
^^^^^^^^^^^^^^^
This element contains one or more ``<A>``, ``<Produces>``, or ``<Consusmes>`` elements.

.. list-table:: <Process> Attributes
   :widths: 10 10 10 10
   :header-rows: 1

   * - Attribute
     - Required
     - Default
     - Values
   * - name
     - yes
     - (none)
     - text
   * - desc
     - no
     - (none)
     - str
   * - enabled
     - no
     - "1"
     - boolean
   * - extend
     - no
     - "0"
     - boolean

<Stream>
^^^^^^^^^^^^^^^
This element contains one or more ``<Component>`` elements.

*(Currently has <Temperature> and <Pressure> subelements, but perhaps these should be attributes?*

.. list-table:: <Stream> Attributes
   :widths: 10 10 10 10
   :header-rows: 1

   * - Attribute
     - Required
     - Default
     - Values
   * - name
     - yes
     - (none)
     - text
   * - number
     - no
     - (none)
     - int
   * - src
     - yes
     - (none)
     - str
   * - dst
     - yes
     - (non)
     - str

<Component>
^^^^^^^^^^^^^^^^
Component encloses an optional numerical value for exogenously-defined component flow rate.

.. list-table:: <Component> Attributes
   :widths: 10 10 10 10
   :header-rows: 1

   * - Attribute
     - Required
     - Default
     - Values
   * - name
     - yes
     - (none)
     - text
   * - phase
     - yes
     - "solid", "liquid" or "gas")
     - str
   * - unit
     - yes
     - (none)
     - str

<Produces>
^^^^^^^^^^^^^^^^
Contains a string indicating the generic name for a substance produced by the ``<Process>``.
This is used in bypassing Processes.

<Consumes>
^^^^^^^^^^^^^^^^
Contains a string indicating the generic name for a substance consumed by the ``<Process>``.
This is used in bypassing Processes.


attributes.xml
----------------

<Attributes>
^^^^^^^^^^^^^

.. saved for reference link format only
.. This element identifies a :doc:`rewrite set <rewrites-xml>` by name.
.. The rewrite set must be defined in a file identified as an argument
.. to the :py:func:`pygcam.query.runBatchQuery`, on the command-line to
.. the :ref:`query sub-command <query>`, or by setting a value for
.. the config variable ``GCAM.RewriteSetsFile``.

This is the top-level element in the `attributes.xml` file. It accepts
no attributes and contains only ``<Class>`` elements.

<Class>
^^^^^^^^^
This element describes attributes associated with an OPGEE class, whose
name is provide by the `name` attribute. ``<Class>`` elements contain
any number of ``<Options>`` and ``<AttrDef>`` elements.

.. list-table:: <Class> Attributes
   :widths: 10 10 10 10
   :header-rows: 1

   * - Attribute
     - Required
     - Default
     - Values
   * - name
     - yes
     - (none)
     - text

<Options>
^^^^^^^^^^^^

This element defines a named set of legal values. Both the `name` and
`default` attributes are required. The ``<Options>`` element contains
one or more (more usefully, two or more) ``<Option>`` elements.

.. list-table:: <Options> Attributes
   :widths: 10 10 10 10
   :header-rows: 1

   * - Attribute
     - Required
     - Default
     - Values
   * - name
     - yes
     - (none)
     - text
   * - default
     - yes
     - (non)
     - text

<Option>
^^^^^^^^^^^^

Describes a single option with an ``<Options>`` element. An optional
`desc` (description) attribute can provide a short explanation of the
option. The ``<Option>`` element contains the value for this alternative,
e.g.,

.. code-block::

    <Options name="ecosystem_C_richness" default="Moderate">
      <Option desc="Low carbon richness (semi-arid grasslands)">Low</Option>
      <Option desc="Moderate carbon richness (mixed)">Moderate</Option>
      <Option desc="High carbon richness (forested)">High</Option>
    </Options>

.. list-table:: <Option> Attributes
   :widths: 10 10 10 10
   :header-rows: 1

   * - Attribute
     - Required
     - Default
     - Values
   * - desc
     - no
     - (none)
     - text

<AttrDef>
^^^^^^^^^^^
This element defines a single attribute, including its name, description,
Python type, and unit. This element can also optionally refer to an ``<Options>``
element describing valid values for this attribute.

.. list-table:: <AttrDef> Attributes
   :widths: 10 10 10 10
   :header-rows: 1

   * - Attribute
     - Required
     - Default
     - Values
   * - name
     - yes
     - (none)
     - text
   * - desc
     - no
     - (none)
     - text
   * - type
     - no
     - str
     - text
   * - unit
     - no
     - (none)
     - text
   * - options
     - no
     - (none)
     - text
   * - delete
     - no
     - "0"
     - boolean

The ``delete`` attribute is used only by user-defined files. If the value
of the attribute is "1", "yes", or "true" (case insensitive), and a corresponding
value exists in the built-in XML structure, the built-in element and all elements
below it in the hierarchy are deleted before the new element is added.
