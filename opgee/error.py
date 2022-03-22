'''
.. Error classes

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
'''


class OpgeeException(Exception):
    pass


# Parent of the two exceptions thrown to stop process cycles
class OpgeeStopIteration(Exception):
    def __init__(self, reason):
        self.reason = reason

class OpgeeMaxIterationsReached(OpgeeStopIteration):
    """Thrown when iterations have reached Model's ``max_iterations``"""
    pass

class OpgeeIterationConverged(OpgeeStopIteration):
    """Thrown when a Process's change variables have all changed less than Model's
       ``iteration_epsilon`` between runs.
    """
    pass

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


class FileFormatError(OpgeeException):
    """
    Indicate a syntax error in a user-managed file.
    """
    pass


class XmlFormatError(FileFormatError):
    pass


class ModelValidationError(FileFormatError):
    pass


class ConfigFileError(FileFormatError):
    """
    Raised for errors in user's configuration file.
    """
    pass


class CommandlineError(OpgeeException):
    """
    Command-line arguments were missing or incorrectly specified.
    """
    pass


class BalanceError(OpgeeException):
    """
    Mass or Energy balances are fail
    """
    def __init__(self, proc_name, mass_or_energy, message=None):
        self.proc_name = proc_name
        self.mass_or_energy = mass_or_energy
        self.message = message

    def __str__(self):
        return f"{self.mass_or_energy} is not balanced in {self.proc_name}" + \
               (f": {self.message}" if self.message else "")


class ZeroEnergyFlowError(OpgeeException):
    """
    Zero energy flow at system boundary, so cannot compute CI
    """
    def __init__(self, stream, message=None):
        self.stream = stream
        self.message = message

    def __str__(self):
        return (f"Zero energy flow rate for {self.stream.boundary} boundary stream {self.stream}" +
                (f": {self.message}" if self.message else ""))

#
# MCS-related exceptions
#
class McsException(Exception):
    'Base class for MCS-related errors.'
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class McsUserError(McsException):
    'The user provided an incorrect parameter or failed to provide a required one.'
    pass

class McsSystemError(McsException):
    'Some application-related runtime error.'
    pass

class IpyparallelError(McsSystemError):
    pass

class FileExistsError(McsSystemError):
    def __init__(self, filename):
        self.message = "File %r already exists" % filename

    # def __str__(self):
    #     return repr(self.message)

class FileMissingError(McsSystemError):
    def __init__(self, filename):
        self.message = "File %r is missing" % filename

class ShellCommandError(McsSystemError):
    def __init__(self, msg, exitStatus=0):
        self.message = msg
        self.exitStatus = exitStatus

    def __str__(self):
        statusMsg = " exit status %d" % self.exitStatus if self.exitStatus else ""
        return "ShellCommandError: %s%s" % (statusMsg, self.exitStatus)

class BaseSpecError(McsSystemError):
    filename = ''
    lineNum = 0

    def __init__(self, message):
        if self.filename and self.lineNum:
            self.message = 'File %s, line %i: ' % (self.filename, self.lineNum) + message
        else:
            self.message = message

class DistributionSpecError(BaseSpecError):
    pass
