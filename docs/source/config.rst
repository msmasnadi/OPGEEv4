Configuration System
=============================

The ``opg`` script relies on a configuration file to:

  * define the location of essential and optional files,
  * allow the user to set defaults for key command-line arguments to scripts, and
  * define both global default and user-specific values for all parameters.

The configuration file and variables are described below.

.. seealso::
   See :doc:`opgee.config` for documentation of the API to the configuration system.

   ``opgee`` uses the Python :mod:`ConfigParser` package. See the documentation
   there for more details.


Configuration file sections
----------------------------
The configuration file is divided into sections indicated by a name within square brackets.
All variable declarations following a section declaration, until the next section
declaration (if any) appear in the declared section.

Default section
^^^^^^^^^^^^^^^^^^^^^^
Default values are defined in the ``[DEFAULT]`` section. When ``opgee`` requests the value
of a variable from a project section (see below), the default value is returned if the
variable is not defined in the project section. Variables whose values apply to multiple
projects can be defined conveniently in the ``[DEFAULT]`` section.

All pre-defined ``opgee`` variables are defined in the ``[DEFAULT]`` section,
allowing them to be overridden on a project-by-project basis.

Project sections
^^^^^^^^^^^^^^^^^^^^^^
Each project must have its own section. For example, to setup a project called,
say, "myproj", I would create the section ``[myproj]``. Following this, I would define
variables particular to this project.

.. _opgee-cfg:

The configuration files
-----------------------
There are up to 4 configuration files read, two of which are user-modifiable:

  #. First, ``opgee/etc/system.cfg`` is read from within the ``opgee`` package. This
     defines all known config variables and provides their default values as described
     below. The values in this file are the appropriate values for Linux and similar systems.
     *This file should not be modified by the user.*

  #. Next, a platform-specific file is read, if it exists. Currently, the only such
     files are ``opgee/etc/Windows.cfg`` and ``opgee/etc/Darwin.cfg``, read on Windows
     and Macintosh systems, respectively. (N.B. "Darwin" is the official platform name
     for the Macintosh operating system.) *These files should not be modified by the user.*

  #. Next, if the environment variable ``OPGEE_SITE_CONFIG`` is defined, it should
     refer to a configuration file that defines site-specific settings. This file is
     optional; it allows an administrator to consolidate site-specific values to
     simplify configuration for users.

  #. Finally, the user's configuration file is read if it exists; otherwise the
     file is created with the initial contents being a commented-out version of
     ``opgee/etc/system.cfg``. This provides a handy reference to the available parameters
     and their default values.

     * On Linux and OS X, the user's configuration file is found in ``$HOME/opgee.cfg``

     * On Windows, the file ``opgee.cfg`` will be stored in the directory identified
       by the first of the following environment variables defined to have a non-empty
       value: ``OPGEE_HOME``, ``HOMESHARE``, and ``HOMEPATH``. The
       first variable, ``OPGEE_HOME`` is known only to opgee, while at least one of
       the other two should be set by Windows.

     * In all cases, the directory in which the configuration file is located is
       assigned to the opgee configuration variable ``Home``.

The values in each successive configuration file override default values for
variables of the same name that are set in files read earlier. Values can also be set in
project-specific section. Thus when a user specifies a project to operate on, either on the
command-line to :doc:`opg` or as the value of ``OPGEE.DefaultProject`` in ``$HOME/opgee.cfg``,
the project-specific values override any values set in ``[DEFAULT]`` sections.

For example, consider the following values in ``$HOME/opgee.cfg``:

.. code-block:: cfg

    [DEFAULT]
    OPGEE.DefaultProject = test
    OPGEE.LogConsole = True
    OPGEE.ShowStackTrace = False

    [test]
    # example of setting different logging levels for individual modules
    OPGEE.LogLevel = INFO, .core:DEBUG, .processes.reservoir_well_interface:DEBUG

    # example of identifying user-defined Process subclasses
    OPGEE.ClassPath = %(Home)s/tmp/opgee_procs.py

    # example of adding new elements to stream components
    OPGEE.StreamComponents = foo, bar ,baz

    # show full stack trace on error (useful mostly for developers)
    OPGEE.ShowStackTrace = True

The default value for ``OPGEE.ShowStackTrace`` is ``False``, meaning that if errors are
raised in the Python code, a full function call stack trace will not be displayed. The
project ``test`` overrides this with the value ``True``.

The available parameters and their default values are described below.


Editing the user configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
You can edit the configuration file, ``$HOME/opgee.cfg``, with any editor capable of
working with plain text, i.e., not a word-processor such as Word. Use the command
``opg config -e`` to invoke an editor on the configuration file.

The command invoked by ``opg config -e`` to edit the config file is the value of the
configuration parameter ``OPGEE.TextEditor``, which defaults to a system-appropriate
value shown in the table below. Set this value in the configuration file to invoke
your preferred editor.

For example, if you prefer the ``emacs`` editor on a Mac, you can add this line to
``~/opgee.cfg`` to cause the Finder to open the file using the emacs application:

.. code-block:: cfg

   OPGEE.TextEditor = open -a emacs

Or, to edit the config file using the PyCharm app, use this:

.. code-block:: cfg

   OPGEE.TextEditor = open -a PyCharm

If the editor command is not found on your execution ``PATH``, you can specify the
full pathname. Use quotes around the path if it includes spaces, as in the examples
below.

To use Notepad++ on Windows, use the following (adjusted as necessary for your
installation location):

.. code-block:: cfg

     OPGEE.TextEditor = "C:/Program Files/Notepad++/notepad++.exe"

To use PyCharm, use the following -- again, adjusted to match your installation
location:

.. code-block:: cfg

     OPGEE.TextEditor  = "C:/Program Files/JetBrains/PyCharm 2018.1.4/bin/pycharm64.exe"


Invoking the command:

.. code-block:: sh

     opg config -e

will cause the editor to be invoked on your configuration file.


Referencing configuration variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A powerful feature of the configuration system is that variables can be defined in
terms of other variables. The syntax for referencing the value of a variable is to
precede the variable name with ``%(`` and follow it with ``)s``. Thus to reference
variable ``OPGEE.QueryDir``, you would write ``%(OPGEE.QueryDir)s``.

.. note::

   When referencing a variable in the config file, you must include the
   trailing ``s`` after the closing parenthesis, or a Python exception will be raised.

   Also note that variable names are case-sensitive.

Variable values are substituted when a variable's value is requested, not
when the configuration file is read. The difference is that if variable ``A`` is
defined in terms of variable ``B``, (e.g., ``A = %(B)s/something/else``), you can
subsequently change ``B`` and the value of ``A`` will reflect this when ``A`` is
accessed by ``opgee``.

All known variables are given default values in the opgee system files. Users
can create variables in any of the user controlled config files, if desired.

Environment variables
~~~~~~~~~~~~~~~~~~~~~~~
All defined environmental variables are loaded into the config parameter space before
reading any configuration files, and are accessible with a prefix of ``$``, as in a
UNIX shell. For example, to reference the environment variable ``SCRATCH``, you can
use ``%($SCRATCH)s``.


Default configuration variables and values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The system default values are provided in the ``opgee`` package in the file
``opgee/etc/system.cfg``, which is listed below. In addition to these values,
several values are read from platform-specific files, as noted above. These
values are shown below.

For Windows:
~~~~~~~~~~~~~~~~~~~~~~~~
.. literalinclude:: ../../opgee/etc/Windows.cfg
   :language: cfg

For MacOS:
~~~~~~~~~~~~~~~~~~~~~
.. literalinclude:: ../../opgee/etc/Darwin.cfg
   :language: cfg

The system defaults file
~~~~~~~~~~~~~~~~~~~~~~~~
.. literalinclude:: ../../opgee/etc/system.cfg
   :language: cfg


.. _logging:

Configuring the logging system
-------------------------------

Setting logging verbosity
^^^^^^^^^^^^^^^^^^^^^^^^^^
When the :doc:`opg` runs, or when opgee functions are called from your
own code, diagnostic and informational messages are printed. You can control
the level of output by setting the ``OPGEE.LogLevel`` in your ``opgee.cfg``
file. (See :py:mod:`logging` for further details.)

The simplest setting is just one of the following values, in order of
decreasing verbosity: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``FATAL``.
This will apply to all opgee modules.

You can also specify verbosity by module, by specifying a module name and the
level for that module as a comma-separated list of "module:level" strings,
e.g.,:

.. code-block:: cfg

     OPGEE.LogLevel = WARN, .utils:INFO, .core:DEBUG

In this example, the default level is set to ``WARN``, and two opgee modules
have their levels set: opgee.utils is set to INFO, and opgee.core is set to DEBUG.
A user's plugin can also use the logging system.

Console / file logs and message formatting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Note that the module name is shown in the console log messages. Setting
``OPGEE.LogLevel`` to DEBUG produces the maximum number of log messages;
setting it to FATAL minimizes message verbocity.

Other relevant variables are shown here with their default values:

.. code-block:: cfg

    # If set, application logger messages are written here.
    OPGEE.LogFile = %(Home)s/log/opgee.log

    # Show log messages on the console (terminal)
    OPGEE.LogConsole = True

    # Format strings for log files and console messages. Note doubled
    # '%%' required here around logging parameters to avoid attempted
    # variable substitution within the config system.
    OPGEE.LogFileFormat    = %%(asctime)s %%(levelname)s %%(name)s:%%(lineno)d %%(message)s
    OPGEE.LogConsoleFormat = %%(levelname)s %%(name)s: %%(message)s
