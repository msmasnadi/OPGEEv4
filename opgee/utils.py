'''
.. Created on: 2/12/15 as part of pygcam
   Imported into opgee on 3/29/21
   Common functions and data

.. Copyright (c) 2015-2021 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import argparse
import os
import sys

from .config import unixPath
from .error import OpgeeException
from .log import getLogger

_logger = getLogger(__name__)

def ipython_info():
    ip = False
    if 'ipykernel' in sys.modules:
        ip = 'notebook'
    elif 'IPython' in sys.modules:
        ip = 'terminal'
    return ip

#
# Custom argparse "action" to parse comma-delimited strings to lists
#
class ParseCommaList(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed with " % option_strings)

        super(ParseCommaList, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values.split(','))

def splitAndStrip(s, delim):
    items = [item.strip() for item in s.split(delim)]
    return items



# used only in opgee modules
def getBooleanXML(value):
    """
    Get a value from an XML file and convert it into a boolean True or False.

    :param value: any value (it's first converted to a lower-case string)
    :return: True if the value is in ['true', 'yes', '1'], False if the value is
             in ['false', 'no', '0', 'none']. An exception is raised if any other
             value is passed.
    :raises: OpgeeException
    """
    false = ["false", "no", "0", "none"]
    true  = ["true", "yes", "1"]
    valid = true + false

    val = str(value).strip().lower()
    if val not in valid:
        raise OpgeeException(f"Can't convert '{value}' to boolean; must be one of {valid} (case sensitive).")

    return (val in true)

# Function to return current function name, or the caller, and so on up
# the stack, based on value of n.
getFuncName = lambda n=0: sys._getframe(n + 1).f_code.co_name

def coercible(value, pytype, raiseError=True, allow_truncation=False):
    """
    Attempt to coerce a value to `pytype` and raise an error on failure. If the
    value is a pint.Quantity, the value is simply returned.

    :param value: any value coercible to `pytype`
    :param pytype: any Python type or its string equivalent
    :param raiseError: (bool) whether to raise errors when appropriate
    :param allow_truncation: (bool) whether to allow truncation of float to int
    :return: (`pytype`) the coerced value, if it's coercible, otherwise
       None if raiseError is False
    :raises OpgeeException: if the value is a pint.Quantity, it is returned
       unchanged. Otherwise, if not coercible and raiseError is True, error is raised.
    """
    from pint import Quantity

    if isinstance(value, Quantity):
        return value

    # pseudo-type
    def binary(value):
        return 1 if getBooleanXML(value) else 0

    if type(pytype) == str:
        if pytype == 'float':
            pytype = float
        elif pytype == 'int':
            pytype = int
        elif pytype == 'str':
            pytype = str
        elif pytype == 'binary':
            pytype = binary
        else:
            raise OpgeeException(f"coercible: '{pytype}' is not a recognized type string")

    # avoid silent truncation of float to int
    if not allow_truncation and pytype == int and type(value) == float:
        raise OpgeeException(f"coercible: Refusing to truncate float {value} to int")

    try:
        value = pytype(value)

    except (TypeError, ValueError) as e:
        if raiseError:
            raise OpgeeException("%s: %r is not coercible to %s" % (getFuncName(1), value, pytype))
        else:
            return None

    return value


def flatten(listOfLists):
    """
    Flatten one level of nesting given a list of lists. That is, convert
    [[1, 2, 3], [4, 5, 6]] to [1, 2, 3, 4, 5, 6].

    :param listOfLists: a list of lists, obviously
    :return: the flattened list
    """
    from itertools import chain

    return list(chain.from_iterable(listOfLists))


def mkdirs(newdir, mode=0o770):
    """
    Try to create the full path `newdir` and ignore the error if it already exists.

    :param newdir: the directory to create (along with any needed parent directories)
    :return: nothing
    """
    from errno import EEXIST        # pycharm thinks this is unknown but it's wrong

    try:
        os.makedirs(newdir, mode)
    except OSError as e:
        if e.errno != EEXIST:
            raise

def loadModuleFromPath(module_path, raiseError=True):
    """
    Load a module from a '.py' or '.pyc' file from a path that ends in the
    module name, i.e., from "foo/bar/Baz.py", the module name is 'Baz'.

    :param module_path: (str) the pathname of a python module (.py or .pyc)
    :param raiseError: (bool) if True, raise an error if the module cannot
       be loaded
    :return: (module) a reference to the loaded module, if loaded, else None.
    :raises: OpgeeException
    """
    import importlib.util

    # Extract the module name from the module path
    module_path = unixPath(module_path)
    base = os.path.basename(module_path)
    module_name = base.split('.')[0]

    _logger.debug(f"Loading module {module_path}")

    # Load the compiled code if it's a '.pyc', otherwise load the source code
    module = None

    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    except Exception as e:
        errorString = f"Can't load module '{module_name} from path '{module_path}': {e}"
        if raiseError:
            raise OpgeeException(errorString)

    return module
