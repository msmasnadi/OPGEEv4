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
-------------------

.. automodule:: opgee.processes.CO2_injection_well
   :members:

.. automodule:: opgee.processes.CO2_membrane
   :members:

.. automodule:: opgee.processes.CO2_reinjection_compressor
   :members:

.. automodule:: opgee.processes.LNG_liquefaction
   :members:

.. automodule:: opgee.processes.LNG_regasification
   :members:

.. automodule:: opgee.processes.LNG_transport
   :members:

.. automodule:: opgee.processes.VRU_compressor
   :members:

.. automodule:: opgee.processes.acid_gas_removal
   :members:

.. automodule:: opgee.processes.bitumen_mining
   :members:

.. automodule:: opgee.processes.crude_oil_dewatering
   :members:

.. automodule:: opgee.processes.crude_oil_stabilization
   :members:

.. automodule:: opgee.processes.crude_oil_storage
   :members:

.. automodule:: opgee.processes.demethanizer
   :members:

.. automodule:: opgee.processes.dilution_transport
   :members:

.. automodule:: opgee.processes.downhole_pump
   :members:

.. automodule:: opgee.processes.drilling
   :members:

.. automodule:: opgee.processes.exploration
   :members:

.. automodule:: opgee.processes.flaring
   :members:

.. automodule:: opgee.processes.gas_dehydration
   :members:

.. automodule:: opgee.processes.gas_distribution
   :members:

.. automodule:: opgee.processes.gas_gathering
   :members:

.. automodule:: opgee.processes.gas_lifting_compressor
   :members:

.. automodule:: opgee.processes.gas_partition
   :members:

.. automodule:: opgee.processes.gas_reinjection_compressor
   :members:

.. automodule:: opgee.processes.gas_reinjection_well
   :members:

.. automodule:: opgee.processes.heavy_oil_dilution
   :members:

.. automodule:: opgee.processes.heavy_oil_upgrading
   :members:

.. automodule:: opgee.processes.natural_gas_liquid
   :members:

.. automodule:: opgee.processes.post_storage_compressor
   :members:

.. automodule:: opgee.processes.pre_membrane_chiller
   :members:

.. automodule:: opgee.processes.pre_membrane_compressor
   :members:

.. automodule:: opgee.processes.reservoir_well_interface
   :members:

.. automodule:: opgee.processes.ryan_holmes
   :members:

.. automodule:: opgee.processes.separation
   :members:

.. automodule:: opgee.processes.sour_gas_compressor
   :members:

.. automodule:: opgee.processes.sour_gas_injection
   :members:

.. automodule:: opgee.processes.steam_generation
   :members:

.. automodule:: opgee.processes.storage_compressor
   :members:

.. automodule:: opgee.processes.storage_separator
   :members:

.. automodule:: opgee.processes.storage_well
   :members:

.. automodule:: opgee.processes.transmission_compressor
   :members:

.. automodule:: opgee.processes.venting
   :members:

.. automodule:: opgee.processes.water_injection
   :members:

.. automodule:: opgee.processes.water_treatment
   :members:

