Calculating Carbon Intensity
==============================

OPGEE calculates *carbon intensity* (CI) as the total CO\ :sub:`2`-equivalent emissions divided
by the flow of either oil or gas at one of possibly multiple system boundaries. Emission and flows
are represented as the quantities used or emitted per day.

The user can select functional units of "1 MJ Oil" or "1 MJ Gas" by setting the
``functional_unit`` attribute. Total daily emissions are divided by the daily flow of oil or
gas to produce CI values with units of CO\ :sub:`2`\ -eq MJ\ :sup:`-1`\ .

Emissions
------------

Total CO\ :sub:`2`\ -equivalent emissions are computed as the sum of a designated set of
greenhouse gases (GHG; see below), weighted by the user's choice of global warming
potential (GWP) values, for all processes in an oil or gas field, plus upstream emissions
per unit of imported energy (e.g., grid electricity or pipeline gas.)

The GHGs tracked by OPGEE processes are:

* CO\ :sub:`2`
* CO
* CH\ :sub:`4`
* N\ :sub:`2`\ O
* VOC (non-methane volatile organic compounds)

Emissions of carbon monoxide (CO), carbon dioxide (CO\ :sub:`2`), methane (CH\ :sub:`4`),
volatile organic compounds (VOC), and nitrous oxide (N\ :sub:`2`\ O) from each ``Process``
are tracked in units of Mg/day, subdivided into the following categories:

* Combustion – emissions resulting from fuel combustion for energy use
* Land-use – emissions resulting from land-use changes at the Field
* Venting – intentionally released gases
* Flaring – combustion of gases without energy use
* Fugitives – unintentional release of gases, e.g., from leaking valves or pipes
* Other


Emissions are stored in a pandas ``DataFrame`` in the :py:class:`Emissions <opgee.emissions>`
class in the file emissions.py.

Global Warming Potentials
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Users can choose which set of GWP values to use by setting attributes ``GWP_horizon``
(20 or 100) and ``GWP_version``, which is one of the following:

* AR4 -- the 4th Assessment Report
* AR5 -- the 5th Assessment Report
* AR5_CCF -- AR5 with carbon cycle feedbacks).

The values associated with these choices are shown below.

.. list-table:: 100-year Global Warming Potentials
   :widths: 6 6 6 6
   :header-rows: 1

   * - Gas
     - AR4
     - AR5
     - AR5_CCF
   * - CO\ :sub:`2`
     - 1
     - 1
     - 1
   * - CO
     - 1.6
     - 2.7
     - 5.3
   * - CH\ :sub:`4`
     - 25
     - 28
     - 34
   * - VOC
     - 3.1
     - 4.5
     - 4.5
   * - N\ :sub:`2`\ O
     - 298
     - 265
     - 298

.. list-table:: 20-year Global Warming Potentials
   :widths: 6 6 6 6
   :header-rows: 1

   * - Gas
     - AR4
     - AR5
     - AR5_CCF
   * - CO\ :sub:`2`
     - 1
     - 1
     - 1
   * - CO
     - 7.65
     - 7.65
     - 18.6
   * - CH\ :sub:`4`
     - 72
     - 84
     - 86
   * - VOC
     - 14
     - 14
     - 14
   * - N\ :sub:`2`\ O
     - 289
     - 264
     - 298


Energy use
------------------
Each Process in OPGEE tracks its own energy consumption in units of million BTUs (mmbtu)
per day, subdivided into the following categories:

* Natural gas
* Upgrader proc. gas
* Natural gas liquids
* Crude oil
* Diesel
* Residual fuel
* Petroleum coke (petcoke)
* Electricity

The structure is implemented as a pandas ``Series`` in the :py:class:`Energy <opgee.energy>` class in
the file energy.py.

System Boundaries
-------------------

OPGEE models can define one or more system boundaries which define the set of processes
to include when calculating CI. The standard boundaries are *Production*, *Transportation*,
and *Distribution*. The *Production* boundary is defined where oil or gas leaves the field
itself, while the *Tranportation* boundary includes transport (by vehicle or pipeline) to
refineries or other downstream processing facilities.

**TODO: define distribution boundary**

Additional boundaries may be defined by the user by setting the configuration variable
``OPGEE.Boundaries``. The default value of this variable is:

``OPGEE.Boundaries = Production, Transportation, Distribution``

