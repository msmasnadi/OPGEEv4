[![Build Status](https://travis-ci.com/Stanford-EAO/OPGEEv4.svg?token=qVku1FaPpCm5v3f1zYpw&branch=master)](https://travis-ci.com/Stanford-EAO/OPGEEv4)
[![codecov](https://codecov.io/gh/Stanford-EAO/OPGEEv4/branch/master/graph/badge.svg?token=NVziMt7tdD)](https://codecov.io/gh/Stanford-EAO/OPGEEv4)
[![Coverage Status](https://coveralls.io/repos/github/Stanford-EAO/OPGEEv4/badge.svg?branch=master&t=xSjoF0)](https://coveralls.io/github/Stanford-EAO/OPGEEv4?branch=master)

# OPGEE v4

OPGEEv4 is implemented as the `opgee` Python package, which provides classes, functions, 
scripts, and data that implement the OPGEE model.

## Core functionality

OPGEEv4 is a tool for translating a physical description of a set of oil and gas fields and their 
constituent conversion and transport processes into a runnable LCA model. OPGEE reads a model 
description file, written in XML format, which drives the instantiation of classes representing 
each LCA component, connecting these as required to implement the corresponding model.

OPGEEv4 is a Python implementation of the Excel-based OPGEEv3. Version 4, however, is implemented
as a more general platform supporting the creation of connected processes and streams that define
an ordered system of processing steps and flows among processes. The functionality of the processes
is defined by subclasses of a generic `Process` class, instances of which are created as defined
in the input XML file.

The main features of OPGEEv4 are:

* Ability to define oil and gas fields and all their attendant processes and streams

* Ordered execution of processes, allowing for cyclic processes

* Tracking of energy use, including imports and exports to/from the field

* Tracking of greenhouse gas emissions

* Calculation of carbon intensity (CI) for oil or gas

* Browser-based graphical user interface (GUI) to view the process and stream network, run the model, modify parameters, and view results

* Graphical display of energy use and emissions by process or aggregation of processes

* Ability to customize many aspects of the system to add new flows to streams, new processes and aggregates, and more.

* Support for Monte Carlo simulation

## How do I get set up?

* Documentation is available at http://opgee.readthedocs.io/.

## Who do I talk to?

* TBD

# Release Notes

## Version 4.1.0 (2024-03-11)

* Improved performance 
* Merged 3 different run commands (run, runsim, runmany) into a unified "run" command (more below)
* Updated model XML format (more below)

### Unified run command
* User can select to generate "simple" or "detailed" results in one or more CSV files.
* OPGEE can run in parallel on a single multi-processor node or across a SLURM cluster,
  returning either "simple" or "detailed" results.
* OPGEE can run multiple fields in parallel or multiple instances of a single field in Monte Carlo mode.
* User can choose how many OPGEE runs (packets) to perform in each worker process.

### Updated model XML format
* The only change is that the `<Analysis>` element can no longer contain `<Field>` elements. 
  Instead, the element `<FieldRef>` is used inside an `<Analysis>` element,
  and all `<Field>` elements appear directly under the `<Model>` element.
* The new `update` subcommand is provided to convert old-format model XML files to this new format.

## Version 4.0.0 (not tagged)
* We did not tag a release 4.0.0

## Version 4.0.0-alpha.0 (2022-03-01)

* First alpha version made public. Still testing against Excel version and adding essential features.

