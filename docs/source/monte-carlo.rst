Monte Carlo Simulation
========================

.. note::
   This page is under development.

Overview
---------

OPGEE support for Monte Carlo Simulation includes:

  * The gensim :doc:`subcommand <opgee.subcommand>`, which reads a file describing
    probability distributions for model attributes and generates a file containing
    data values drawn from these distributions for a defined number of trials.

  * The runsim subcommand, which runs a simulation, optionally by distributing the
    simulation across multiple processors.

These are defined in more detail below.

Generating a simulation
-------------------------

* gensim

  * supported distributions
  * CSV file and format
  * simulation directory and contents
  * merged XML copied to simulation directory

Running a simulation
----------------------

* runsim

  * running a trial
  * multiprocessing
  * results
