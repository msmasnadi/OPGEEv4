[![Build Status](https://travis-ci.com/Stanford-EAO/OPGEEv4.svg?token=qVku1FaPpCm5v3f1zYpw&branch=master)](https://travis-ci.com/Stanford-EAO/OPGEEv4)
[![codecov](https://codecov.io/gh/Stanford-EAO/OPGEEv4/branch/master/graph/badge.svg?token=NVziMt7tdD)](https://codecov.io/gh/Stanford-EAO/OPGEEv4)
[![Coverage Status](https://coveralls.io/repos/github/Stanford-EAO/OPGEEv4/badge.svg?branch=master&t=xSjoF0)](https://coveralls.io/github/Stanford-EAO/OPGEEv4?branch=master)

# OPGEE v4

`opgee` is a Python package that provides classes, functions, and scripts that implement the OPGEE model.

## Core functionality

* TBD

## How do I get set up?

* Eventually, see http://opgee.readthedocs.io/en/latest/install.html. But that's not hosted yet.

## Who do I talk to?

* TBD

## To Do
* Finish developing facility merge user model/attribute defs with default (or other) defs.

* Handle Fuel Gas Imports
  * Exchanges of energy carriers from outside system boundary
  * Add a Natural Gas Pipeline process: exports generate a credit (depends on functional unit)


* Design
    * How best to show results

* Rich
    * Smart defaults
    * MCS
    * GUI development
        * Graphing
        * dynamic changes to settings -> re-run
        * can we keep display mostly consistent between structures?
    * Save and reload (.opg file format)

* Adam
    * Legal conversation: licensing / flavor of open source
        * Keeping Rich's code open source

* Wennan
    * outstanding procecesses
    * better treatment of fugitives
    * incorporate external developments
        * Jeff's fugitives model
        * John Chan's flaring model
    * streams that leave system boundary
    * generic mass balance check
    * documentation
    * TODOs 
    
* Someday maybe
    * Conversion of R code that builds the database into something managable
    * Creation XML from 300 fields in OPGEEv3

# Release Notes

## Version 4.0.0-alpha.0 (xx-xxx-2021)
