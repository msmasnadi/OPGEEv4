What is OPGEE?
====================

The ``opgee`` package comprises a set of data files, Python modules, and a main driver script that
implement the `Oil Production Greenhouse gas Emissions Estimator <https://eao.stanford.edu/research-areas/opgee>`_ (OPGEE).

The main features include:

  * **Cross-platform capability** on Windows, Mac OS X, and Linux.

  ..

  * **Installer scripts** to simplify installation of tools on users’ computers.

  ..

  * **User documentation** for all of the above. (This website!)

Users can control several aspects of ``opgee`` through a :doc:`configuration file <config>`
found in ``${HOME}/opgee.cfg``. When :doc:`opg` is run the first time, a simple, default
configuration file is created.

The main script (:doc:`opg`) implements several "subcommands" that provide access to various
features such as running models, graphing aspects of the LCA model and class structure.
The script implements a :doc:`plug-in <opgee.subcommand>`
architecture allowing users to customize :doc:`opg <opg>` and avoid a proliferation
of scripts. The available subcommands for general use include:

   * ``config`` displays the values of configuration parameters and edits the
     user's configuration file.

   * ``gui`` runs a local web server that provides a browser-based graphical
     user interface (GUI) at the address http://127.0.0.1:8050.

   * ``run`` reads an XML input file and runs one or more steps of an analysis,
     and these steps typically invoke other sub-commands as required.

Design Goals
--------------------


