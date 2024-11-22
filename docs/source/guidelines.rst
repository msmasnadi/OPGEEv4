Developer Guidelines
====================

A key design goal of the ``opgee`` package is to facilitate extension to and customization of
the built-in XML model description. We have tried to adhere to the following guidelines in
developing the model, both to make customization easier and to keep the code organized.

.. examples for
.. :doc:`configuration file <config>`
.. :doc:`opg` implements several "subcommands" that provide access to various


Code organization
--------------------

The Python files in the `opgee` directory define the generic oil and gas LCA framework.
All built-in subclasses of ``Process`` are located in the subdirectory `processes`, along
with some support files shared by those processes.

Other subdirectories include:

* `bin` -- support scripts

* `built_ins` -- plug-ins that define subcommands of the :doc:`opg <opg>` command-line script.

* `etc` -- XML model description files, XML schema files (used for validation of model XML files),
  configuration default files (including operating system specific defaults), description of
  units to extend the set built into the ``pint`` package.

* `gui` -- Python files implementing the browser-based GUI using the `plotly "dash" package <https://dash.plotly.com>`_

* `mcs` -- Support for Monte Carlo Simulation

* `processes` -- implementations of ``Process`` subclasses and other support code

* `tables` -- CSV files that are loaded on demand by the ``TableManager`` and
  loaded into pandas DataFrames


XML organization
------------------

The built-in model XML is organized into the following files:

* `attributes.xml` holds attribute definitions, i.e., metadata defining attributes,
  including name, type, default value, description, and so on. Attributes must be
  defined before they can be assigned values in ``Analysis``, ``Field``, ``Process``,
  ``Stream`` or ``Aggregate`` elements in the model XML.

* `opgee.xml` holds the definition of the default fields and analyses.

* `opgee.xsd` holds the XML schema definition for all model classes and those
  used to define attribute metadata: ``AttrDef``, ``ClassAttrs``, ``Options``,
  ``Option``, and ``Requires``.


.. |br| raw:: html

   <br />

Minimize explicit dependencies to maximize flexibility
--------------------------------------------------------

To facilitate customization of the built-in model we try to adhere to the following
principles:

1. **Do not hardcode dependencies among processes.** |br|
   Reference streams by their contents, not by an expected source or destination, as
   the latter may break if a user modifies the process network. Use the ``Process`` methods
   :py:func:`~opgee.process.Process.find_input_stream()`,
   :py:func:`~opgee.process.Process.find_input_streams()`,
   :py:func:`~opgee.process.Process.find_output_stream()`, and
   :py:func:`~opgee.process.Process.find_output_streams()`.

2. **Keep stream contents as generic as possible.** |br|
   Avoid names that encode the endpoints of the stream, using instead as generic a name
   for the contents as possible. Use content names that describe the main contents of the
   stream, like "oil" or "dehydrated gas". **Do not** include the name of the source or
   destination processes in the contents.

3. **Store data that needs to be shared with other processes in the Field instance.** |br|
   Use the API provided by ``Field`` methods :py:func:`~opgee.field.Field.save_process_data()`
   and :py:func:`~opgee.field.Field.get_process_data()`.

