Installation
==================

Install opgee in an Anaconda virtual environment
---------------------------------------------------

1. Download and install `Anaconda <https://www.anaconda.com/download>`_ for your
   platform. Note that ``opgee`` requires Python 3.7 or later.

The most convenient way to install and manage a scientific Python environment
is to use the free `Anaconda <https://www.anaconda.com/download>`_ distribution.
Anaconda includes most of the scientific and statistical modules used by ``opgee``.
You can, however, use any installation of Python if you prefer. Without
Anaconda you may have to install more packages. Note that all development and
testing of opgee uses Anaconda. Follow the installation instructions for your
platform.

   * Download the .yml file for your platform from the OPGEEv4 github repository:

       * `py3_opgee_win10.yml <https://github.com/arbrandt/OPGEEv4/blob/master/py3_opgee_win10.yml>`_
       * `py3_opgee_macos.yml <https://github.com/arbrandt/OPGEEv4/blob/master/py3_opgee_macos.yml>`_
       * `py3_opgee_linux.yml <https://github.com/arbrandt/OPGEEv4/blob/master/py3_opgee_linux.yml>`_

3. Run the following command, replacing the ``/path/to/file.yml`` with the
   path to the file you downloaded in step 2:

  .. code-block:: bash

     # Replace "/path/to/file.yml" with path to the file you downloaded
     conda env create -f /path/to/file.yml

4. Activate the new environment:

  .. code-block:: bash

     conda activate opgee

5. Finally, install the opgee package into the newly created environment::

     pip install opgee

.. seealso::

   See the `conda <https://conda.io/docs/user-guide/tasks/manage-environments.html>`_
   documentation for further details on managing environments.


.. _option2:


Working with opgee source code
--------------------------------

If you are interested in working with the source code (e.g., writing plugins or
adding functionality), you should clone the code repository (https://github.com/arbrandt/OPGEEv4)
to create a local copy. You can then install ``opgee`` in "developer" mode using the ``setup.py``
script found in the top-level ``OPGEEv4`` directory. This creates links from the
installed package to the source code repository so changes to the source code are
available immediately without requiring reinstallation of ``opgee``.

.. code-block:: bash

   # Uninstall opgee if you installed it previously: this avoids
   # potential conflicts with previously installed files.
   pip uninstall opgee

   # Change directory to where you want the opgee folder to be "cloned"
   cd (wherever you want)

   # Clone the git repository
   git clone https://github.com/arbrandt/OPGEEv4
   cd OPGEEv4

   # Install opgee in developer mode
   python setup.py develop

The ``setup.py`` script uses a Python module called ``setuptools``. On Mac OS X and
Linux, ``setup.py`` installs ``setuptools`` automatically. Unfortunately, this has
been less reliable on Windows, so if the commands above fail, you will have to install
``setuptools``. To install ``setuptools`` manually, run this command in a terminal:

.. code-block:: bash

   conda install setuptools
