OPGEE Processes
=====================

This module contains the subclasses of Process defined in the opgee package.

Guidelines for documenting Process subclasses
-----------------------------------------------

The following elements of each process should be defined in the class header comment:

* Attributes defined for the class (no need to duplicate generic Process attributes)

* Required input and output streams, by stream type

* Optional input and output streams, by stream type (i.e., those that will be processed if present)

* Whether the process has special handling to exit the run() method unless all required input streams
  have data. [If we explicitly declare required stream types, we can handle this check with a common
  function used by all such processes.]

  * More generally, any conditions that cause the process to return without writing to output streams.

* Any data stored in, or accessed from the Field class.

* Whether the process defines an impute() method for use in initialization from exogenous data.


Process subclasses
---------------------

  .. toctree::
   :glob:

   processes/*
