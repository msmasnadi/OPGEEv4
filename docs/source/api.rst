OPGEE Python API
===================

See the https://opensource.org/licenses/MIT for license details.

OPGEE Classes
--------------

OPGEEv4 is a tool for translating a physical description of a set of oil fields and their constituent conversion and
transport processes into a runnable LCA model. OPGEE reads a model description file, written in XML format, which
drives the instantiation of classes representing each LCA component, connecting these as required to implement the
corresponding model. Each XML element name (e.g., ``<Analysis>``, ``<Process>``, ``<Stream>``, so on) corresponds to a
Python class of the same name. Each class is instantiated with its instance variables populated by overlaying default
values with values specified in the XML file, and children elements of each element are stored. The nested containers
allow reporting of results at each nesting level.

  .. toctree::
   :maxdepth: 1
   :glob:

   opgee.core
   opgee.processes
   opgee.thermodynamics

Supporting Modules
---------------------

  .. toctree::
   :maxdepth: 1
   :glob:

   opgee.config
   opgee.subcommand
   opgee.utils
