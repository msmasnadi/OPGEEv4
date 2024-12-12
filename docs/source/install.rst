Installation
==================

Note that OPGEEv4 is not currently installable as a Python package from the “pip” package server.
Please follow the instructions below.

Install opgee in an Anaconda virtual environment
---------------------------------------------------

1. Download and install `Anaconda <https://www.anaconda.com/download>`_ for your
   platform. Note that the current version of ``opgee`` has been tested on Python 3.11.

OPGEE has been developed and tested using the free `Anaconda <https://www.anaconda.com/download>`_
distribution. Anaconda includes most of the scientific and statistical modules used by ``opgee``.
You can, however, use any installation of Python if you prefer. Without
Anaconda you will not be able to use the YML file below and may have to install more
packages.

2. Download the YML file from the OPGEEv4 github repository:

       * `py3-opgee.yml <https://raw.githubusercontent.com/msmasnadi/OPGEEv4/refs/heads/master/py3-opgee.yml>`_

     This file has been verified to work correctly on MS Windows, macOS, and Linux.

3. Run the following command, replacing the ``/path/to/py3-opgee.yml`` with the
   path to the file you downloaded in step 1:

  .. code-block:: bash

     # Replace "/path/to/py3-opgee.yml" with path to the file you downloaded
     conda env create -f /path/to/py3-opgee.yml

4. Activate the new environment:

  .. code-block:: bash

     conda activate opgee

5. Clone the OPGEE repository and install the OPGEE package into the activated environment:

  .. code-block:: bash

    git clone https://github.com/msmasnadi/OPGEEv4.git
    cd OPGEEv4
    pip install -e .

which links the installed package back to the source code repo.

.. seealso::

   See the `conda <https://conda.io/docs/user-guide/tasks/manage-environments.html>`_
   documentation for further details on managing environments.
