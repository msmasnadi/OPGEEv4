Monte Carlo Simulation
========================

.. note::
   This page is under development. Needs a section on how it works internally.

Overview
---------

OPGEE support for Monte Carlo Simulation includes:

  * The script ``opgee/bin/combine_wor_data.py``, which reads these input files from the directory
    ``opgee/mcs/etc``:

    * ``Norway_historical_WOR.csv``
    * ``UK_Results.MATLAB.csv``
    * ``WOR_observations_long.csv``

    and combines them to create ``all_wor.csv`` in that same directory. All rows in which "WOR"
    is zero or ``NaN`` are deleted. The ``gensim`` command randomly draws values for fields'
    ``WOR`` attributes from the remaining values.  **Note that this script needs to be run only
    if/when the input files are updated.**

  * The ``csv2xml`` subcommand, which converts a specifically formatted CSV file containing field attributes
    to the XML representation required for running in OPGEE. The primary source file (``opgee/etc/test-fields.csv``)
    is based on data extracted from the OPGEEv3 Excel workbook.

  * The ``gensim`` subcommand which reads ``opgee/mcs/etc/parameter_distributions.csv``,
    a file describing probability distributions for model attributes. ``Gensim`` then generates a file containing
    data values drawn from these distributions for a defined number of trials, with one file generated per
    field explicitly or implicitly identified in the call to ``gensim``.

  * The ``runsim`` subcommand, which runs a simulation, by distributing the simulation across
    simulation across multiple processors. ``Runsim`` can optionally run trials serially in a single process,
    which is useful primarily for debugging. Based on options in ``$HOME/opgee.cfg``, the simulation can
    run on a single multi-processor computer or on a high-performance computing cluster using the SLURM
    job management system.

These scripts and subcommands are described in more detail below.

Generating a simulation
-------------------------

OPGEE uses a two-step process to run simulations. In the first step, the ``gensim`` subcommand creates
a "simulation directory" containing the model XML file, metadata describing the simulation (e.g., number
of trials, which fields are included), and field-specific subdirectories that each contain a file
``trial_data.csv``.

In the second step, the ``runsim`` subcommand creates a software "cluster" (a monitor process communicating
with some number of worker processes) using the ``dask`` package and instructs each worker to run a simulation
on a specified field. Results are saved to a file ``results.csv`` in each field-specific sub-directory of
the simulation directory.

The ``gensim`` subcommand
~~~~~~~~~~~~~~~~~~~~~~~~~~~

  * The `gensim subcommand <opg.html#gensim>`__ currently supports the following distributions, though it is fairly easy to add new ones:

    * Uniform
    * Normal
    * Truncated Normal
    * Lognormal
    * Trianglular
    * Binary
    * Weighted binary
    * Empirical, in which values are drawn randomly from a specified column in a CSV file.

    Other distributions are supported in the code but no by the ``parameter_distributions.csv`` file
    format currently used (more below). These include ``sequence``, which returns a random selection from a given
    list of values;
    ``integers``, which returns an integer value between given min and max values; and
    ``constant``, which always returns the same user-defined value.

Distributions file format
~~~~~~~~~~~~~~~~~~~~~~~~~~

The parameters distributions file is a CSV file with the following columns:

    * ``variable_name`` -- The name of an OPGEE model attribute. These are interpreted as attributes
      of the ``Field`` class unless preceded by a class name and ".". For example, the variable name
      ``ReservoirWellInterface.frac_CO2_breakthrough`` is interpreted as the ``frac_CO2_breakthrough``
      attribute of the ``ReservoirWellInterface`` process.

    * ``distribution_type`` -- one of "Uniform", "Binary", "Normal", "Lognormal", "Triangular", "Emprical".

      * "Uniform" distributions require values in the ``low_bound`` and ``high_bound`` columns.

      * "Normal" and "Lognormal" distributions require values in the ``mean`` and ``SD`` columns.
        If there are values in
        the ``low_bound`` and ``high_bound`` columns convert this to a truncated normal distribution.

      * For "Binary" distributions, a value in the ``prob_of_yes`` column
        converts this to a weighted binary distribution.

      * "Triangular" distributions require values in the ``low_bound``, ``high_bound``, and ``default_value``
        columns.

      * "Empirical" distributions require a pathname to a CSV file, which must have a column whose name
        matches the value in the ``variable_name`` column.

    * ``mean`` -- Used for Normal and Lognormal distributions

    * ``SD`` -- Used for Normal and Lognormal distributions

    * ``low_bound`` and ``high_bound`` -- Used to define "Uniform" and "Triangular" distributions and to
      truncate "Normal" distributions

    * ``prob_of_yes`` -- used to turn a "Binary" distribution into a weighted binary

    * ``default_value`` -- defines the mode of a triangular distribution

    * ``pathname`` -- defines the CSV file to use for empirical data. Note that the same file can be
      used for multiple parameters provided that there is a column name that matches each parameter.

    * ``notes`` -- for documentation only.



Running a simulation
-----------------------

Before running a simulation, the simulation directory must be created using the ``gensim``
sub-command, described above. The simulation directory must be specified using the ``-s/--simulation-dir``
argument to the `runsim subcommand <opg.html#runsim>`__. This directory holds a fully expanded version of the model,
the input data generated from parameter distributions, and after running the simulation, the results
for each field.

The simulation directory contains a sub-directory for each field evaluated, in which the files "results.csv"
and "failures.csv" will be written when all trials for the field have been run.

The ``runsim`` sub-command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``runsim`` command can run simulations in any of three modes:

1. *Serially*, in which one model run is executed at a time. This is the slowest method, but often
   the most convenient to use for debugging. To select serial mode, use the ``-S/--serial`` command-line
   option.

2. If the ``-s/--serial`` option is not used, the simulation mode is determined from the configuration file
   variable ``OPGEE.ClusterType``, which defaults to ``local``. The other recognized value is ``slurm``.

   In local mode, the simulation is run on a single- or multiple-CPU computer. By default,
   ``runsim`` will spawn a process for each available processor. The number of tasks can be
   controlled by the ``-n/--ntasks`` argument to ``runsim``. Each process runs the designated
   number of trials for a field before moving onto any remaining fields.

3. If ``-s/--serial`` is not used, and the value of ``OPGEE.ClusterType`` is ``slurm``, the SLURM
   task management system is used. Note that this option works only on high-performance computing
   (HPC) clusters that use SLURM. In this mode, ``runsim`` submits a designated number of jobs which
   are allocated to available compute nodes. Again, each process runs the required trials for one
   field to completion before starting on any remaining fields. Note that there are several
   :doc:`configuration file <config>` options controlling behavior on SLURM systems.

A full description of all options is available `here <opg.html#runsim>`__.
