Attributes
===========

This section describes the general processing of attributes. Specific attributes are defined
with the object they describe, e.g., Analysis, Field, or Process.

Attribute Definitions
----------------------

Attributes used in model description XML files must be defined in attributes.xml.
(Eventually there will be a way to augment this via the config file.)

Attributes are defined in {opgee}/etc/attributes.xml using the `<AttrDefs>` element.
Definitions include the attribute type (text string, integer, floating point number,
or one of defined set of choices.

All attributes defined in attributes.xml are set to their default value if a value
is not provided in a model description XML file.

Smart Defaults
---------------

To be implemented.

