The "opg" script
===============================

The `opg` script unifies OPGEE functionality into a single script with sub-commands.
Common (built-in) sub-commands are implemented directly in the ``ogpee`` package.
Project-specific features can be added via :ref:`plugins <plugins-label>`.

.. note::

   Quick links to sub-commands:
   :ref:`config <config>`,
   :ref:`collect <collect>`,
   :ref:`csv2xml <csv2xml>`
   :ref:`gensim <gensim>`,
   :ref:`genwor <genwor>`,
   :ref:`graph <graph>`,
   :ref:`gui <gui>`,
   :ref:`merge <merge>`,
   :ref:`run <run>`,
   :ref:`runsim <runsim>`,

Usage
-----
.. argparse::
   :module: opgee.tool
   :func: _getMainParser
   :prog: opg


   config : @replace
      .. _config:

      The config command list the values of configuration variables from ~/opgee.cfg.
      With no arguments, it displays the values of all variables for the default project.
      Use the ``-d`` flag to show only values from the ``[DEFAULT]`` section.

      If an argument ``name`` is provided, it is treated as a substring pattern, unless the
      ``-x`` flag is given (see below). All configuration variables containing the give name
      are displayed with their values. The match is case-insensitive.

      If the ``-x`` or ``--exact`` flag is specified, the argument is treated as an exact
      variable name (case-sensitive) and only the value is printed. This is useful mainly
      for scripting. For general use the substring matching is more convenient.

      Examples:

      .. code-block:: bash

         $ opg config log
         [test]
                       $LOGNAME = rjp
               OPGEE.LogConsole = True
         OPGEE.LogConsoleFormat = %(levelname)s %(name)s: %(message)s
                   OPGEE.LogDir = /Users/rjp/tmp
                  OPGEE.LogFile = /Users/rjp/tmp/opgee.log
            OPGEE.LogFileFormat = %(asctime)s %(levelname)s %(name)s:%(lineno)d %(message)s
                 OPGEE.LogLevel = INFO, .mcs.simulation:DEBUG, .field:INFO, .smart_defaults:DEBUG

         $ opg config -x OPGEE.LogLevel
         INFO, .mcs.simulation:DEBUG, .field:INFO, .smart_defaults:DEBUG



   graph : @before
      .. _graph:


   gensim : @before
      .. _gensim:


   genwor : @before
      .. _genwor:


   gui : @before
      .. _gui:


   merge : @before
      .. _merge:


   run : @before
      .. _run:


   runsim : @before
      .. _runsim:


   collect : @before
      .. _collect:

   csv2xml : @before
      .. _csv2xml:


Extending "opg" using plug-ins
------------------------------
  .. _plugins-label:

The `opg` script will load any python files whose name ends in
``_plugin.py``, found in any of the directories indicated in the config
file variable ``OPGEE.PluginPath``. The value of ``OPGEE.PluginPath`` must
be a sequence of directory names separated by colons (``:``) on Unix-like
systems or by semi-colons (``;``) on Windows.

See :doc:`opgee.subcommand` for documentation of the plug-in API.
