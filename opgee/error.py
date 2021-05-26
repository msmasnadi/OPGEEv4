'''
.. Error classes

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
'''

class OpgeeException(Exception):
    pass

# Thrown when iterations have reached Model's max_iterations or a Process's
# change variable has changed less than Model's iteration_epsilon between runs.
class OpgeeStopIteration(Exception):
    def __init__(self, reason):
        self.reason = reason


class AbstractMethodError(OpgeeException):
    def __init__(self, cls, method):
        self.cls = cls
        self.method = method

    def __str__(self):
        return f"Abstract method {self.method} was called. A subclass of {self.cls.__name__} must implement this method."


class AttributeError(OpgeeException):
    def __init__(self, dict_name, key):
        self.dict_name = dict_name
        self.key = key

    def __str__(self):
        return f"Attribute {self.dict_name} for '{self.key}' was not found"

# Deprecated
# class FileMissingError(OpgeeException):
#     """
#     Indicate that a required file was not found or not readable.
#     """
#     def __init__(self, filename, reason):
#         self.filename = filename
#         self.reason   = reason
#
#     def __str__(self):
#         return "Can't read %s: %s" % (self.filename, self.reason)

class FileFormatError(OpgeeException):
    """
    Indicate a syntax error in a user-managed file.
    """
    pass

class XmlFormatError(FileFormatError):
    pass

# Deprecated
# class FileExistsError(OpgeeException):
#     """
#     Raised when trying to write a file that already exists (if not allowed)
#     """
#     def __init__(self, filename):
#         self.filename = filename
#
#     def __str__(self):
#         return "Refusing to overwrite file: %s" % self.filename

class ConfigFileError(FileFormatError):
    """
    Raised for errors in user's configuration file.
    """
    pass

class CommandlineError(Exception):
    """
    Command-line arguments were missing or incorrectly specified.
    """
    pass
