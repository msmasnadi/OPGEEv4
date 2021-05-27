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

# Deprecated
#import re
#import subprocess
#from contextlib import contextmanager

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

# Deprecated
# _abspath_prog = re.compile(r"^([/\\])|([a-zA-Z]:)")
#
# def is_abspath(pathname):
#     """
#     Return True if pathname is an absolute pathname, else False.
#     """
#     return bool(_abspath_prog.match(pathname))
#
# def get_path(pathname, defaultDir):
#     """
#     Return pathname if it's an absolute pathname, otherwise return
#     the path composed of pathname relative to the given defaultDir.
#     """
#     return pathname if is_abspath(pathname) else pathjoin(defaultDir, pathname)
#
# def queueForStream(stream):
#     """
#     Create a thread to read from a non-socket file descriptor and
#     its contents to a socket so non-blocking read via select() works
#     on Windows. (Since Windows doesn't support select on pipes.)
#
#     :param stream: (file object) the input to read from,
#        presumably a pipe from a subprocess
#     :return: (int) a file descriptor for the socket to read from.
#     """
#     from six.moves.queue import Queue
#     from threading import Thread
#
#     def enqueue(stream, queue):
#         fd = stream.fileno()
#         data = None
#         while data != b'':
#             data = os.read(fd, 1024)
#             queue.put(data)
#         stream.close()
#
#     q = Queue()
#     t = Thread(target=enqueue, args=(stream, q))
#     t.daemon = True # thread dies with the program
#     t.start()
#
#     return q
#
# def digitColumns(df, asInt=False):
#     '''
#     Get a list of columns with integer names (as strings, e.g., "2007") in df.
#     If asInt is True return as a list of integers, otherwise as strings.
#     '''
#     digitCols = filter(str.isdigit, df.columns)
#     return [int(x) for x in digitCols] if asInt else list(digitCols)
#
# @contextmanager
# def pushd(directory):
#     """
#     Context manager that changes to the given directory and then
#     returns to the original directory. Usage is ``with pushd('/foo/bar'): ...``
#
#     :param directory: (str) a directory to chdir to temporarily
#     :return: none
#     """
#     owd = os.getcwd()
#     try:
#         os.chdir(directory)
#         yield directory
#     finally:
#         os.chdir(owd)

# used only in opgee modules
def getBooleanXML(value):
    """
    Get a value from an XML file and convert it into a boolean True or False.

    :param value: any value (it's first converted to a string)
    :return: True if the value is in ['true', 'yes', '1'], False if the value
             is in ['false', 'no', '0']. An exception is raised if any other
             value is passed.
    :raises: OpgeeException
    """
    false = ["false", "no", "0"]
    true  = ["true", "yes", "1"]

    val = str(value).strip().lower()
    if val not in true + false:
        raise OpgeeException("Can't convert '%s' to boolean; must be in {false,no,0,true,yes,1} (case sensitive)." % value)

    return (val in true)

# Deprecated
# def deleteFile(filename):
#     """
#     Delete the given `filename`, but ignore errors, like "rm -f"
#
#     :param filename: (str) the file to remove
#     :return: none
#     """
#     try:
#         os.remove(filename)
#     except:
#         pass    # ignore errors, like "rm -f"
#
# def systemOpenFile(path):
#     """
#     Ask the operating system to open a file at the given pathname.
#
#     :param path: (str) the pathname of a file to open
#     :return: none
#     """
#     import platform
#     from subprocess import call
#
#     if platform.system() == 'Windows':
#         call(['start', os.path.abspath(path)], shell=True)
#     else:
#         # "-g" => don't bring app to the foreground
#         call(['open', '-g', path], shell=False)

# Function to return current function name, or the caller, and so on up
# the stack, based on value of n.
getFuncName = lambda n=0: sys._getframe(n + 1).f_code.co_name

def coercible(value, pytype, raiseError=True, allow_truncation=False):
    """
    Attempt to coerce a value to `type` and raise an error on failure. If the
    value is a pint.Quantity, the value is simply returned.

    :param value: any value coercible to `type`
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

# Deprecated
# def shellCommand(command, shell=True, raiseError=True):
#     """
#     Run a shell command and optionally raise OpgeeException error.
#
#     :param command: the command to run, with arguments. This can be expressed
#       either as a string or as a list of strings.
#     :param shell: if True, run `command` in a shell, otherwise run it directly.
#     :param raiseError: if True, raise `ToolError` on command failure.
#     :return: exit status of executed command
#     :raises: ToolError
#     """
#     _logger.info(command)
#     exitStatus = subprocess.call(command, shell=shell)
#     if exitStatus != 0:
#         if raiseError:
#             raise OpgeeException("\n*** Command failed: %s\n*** Command exited with status %s\n" % (command, exitStatus))
#
#     return exitStatus

def flatten(listOfLists):
    """
    Flatten one level of nesting given a list of lists. That is, convert
    [[1, 2, 3], [4, 5, 6]] to [1, 2, 3, 4, 5, 6].

    :param listOfLists: a list of lists, obviously
    :return: the flattened list
    """
    from itertools import chain

    return list(chain.from_iterable(listOfLists))

# Deprecated
# def ensureExtension(filename, ext):
#     """
#     Force a filename to have the given extension, `ext`, adding it to
#     any other extension, if present. That is, if `filename` is ``foo.bar``,
#     and `ext` is ``baz``, the result will be ``foo.bar.baz``.
#     If `ext` doesn't start with a ".", one is added.
#
#     :param filename: filename
#     :param ext: the desired filename extension
#     :return: filename with extension `ext`
#     """
#     mainPart, extension = os.path.splitext(filename)
#     ext = ext if ext[0] == '.' else '.' + ext
#
#     if not extension:
#         filename = mainPart + ext
#     elif extension != ext:
#         filename += ext
#
#     return filename
#
# def ensureCSV(file):
#     """
#     Ensure that the file has a '.csv' extension by replacing or adding
#     the extension, as required.
#
#     :param file: (str) a filename
#     :return: (str) the filename with a '.csv' extension.
#     """
#     return ensureExtension(file, '.csv')
#
# def saveTextToFile(txt, dirname='', filename=''):
#     """
#     Save the given text to a file in the given directory.
#
#     :param txt: (str) the text to save
#     :param dirname: (str) path to a directory
#     :param filename: (str) the name of the file to create
#
#     :return: none
#     """
#     if dirname:
#         mkdirs(dirname)
#
#     pathname = pathjoin(dirname, filename)
#
#     _logger.debug("Writing %s", pathname)
#     with open(pathname, 'w') as f:
#         f.write(txt)
#
# def mkdirs(newdir, mode=0o770):
#     """
#     Try to create the full path `newdir` and ignore the error if it already exists.
#
#     :param newdir: the directory to create (along with any needed parent directories)
#     :return: nothing
#     """
#     from errno import EEXIST
#
#     try:
#         os.makedirs(newdir, mode)
#     except OSError as e:
#         if e.errno != EEXIST:
#             raise

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
    base        = os.path.basename(module_path)
    module_name = base.split('.')[0]

    _logger.debug('loading module %s' % module_path)

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

# Deprecated
# def importFrom(modname, objname, asTuple=False):
#     """
#     Import `modname` and return reference to `objname` within the module.
#
#     :param modname: (str) the name of a Python module
#     :param objname: (str) the name of an object in module `modname`
#     :param asTuple: (bool) if True a tuple is returned, otherwise just the object
#     :return: (object or (module, object)) depending on `asTuple`
#     """
#     from importlib import import_module
#
#     module = import_module(modname, package=None)
#     obj    = getattr(module, objname)
#     return ((module, obj) if asTuple else obj)
#
# def importFromDotSpec(spec):
#     """
#     Import an object from an arbitrary dotted sequence of packages, e.g.,
#     "a.b.c.x" by splitting this into "a.b.c" and "x" and calling importFrom().
#
#     :param spec: (str) a specification of the form package.module.object
#     :return: none
#     :raises OpgeeException: if the import fails
#     """
#     modname, objname = spec.rsplit('.', 1)
#
#     try:
#         return importFrom(modname, objname)
#
#     except ImportError:
#         raise OpgeeException("Can't import '%s' from '%s'" % (objname, modname))

# Deprecated
# def printSeries(series, label, header='', asStr=False):
#     """
#     Print a `series` of values, with a give `label`.
#
#     :param series: (convertible to pandas Series) the values
#     :param label: (str) a label to print for the data
#     :return: none
#     """
#     import pandas as pd
#
#     if type(series) == pd.DataFrame:
#         df = series
#         df = df.T
#     else:
#         df = pd.DataFrame(pd.Series(series))  # DF is more convenient for printing
#
#     df.columns = [label]
#
#     oldPrecision = pd.get_option('precision')
#     pd.set_option('precision', 5)
#     s = "%s\n%s" % (header, df.T)
#     pd.set_option('precision', oldPrecision)
#
#     if asStr:
#         return s
#     else:
#         print(s)
