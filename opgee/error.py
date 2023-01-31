#
# Error classes
#
# Author: Richard Plevin
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#

class OpgeeException(Exception):
    pass


# Parent of the two exceptions thrown to stop process cycles
class OpgeeStopIteration(OpgeeException):
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


class ModelValidationError(OpgeeException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return f'<{self.__class__.__name__} "{self.msg}">'

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


class McsUserError(OpgeeException):
    pass

class McsSystemError(OpgeeException):
    pass

class DistributionSpecError(OpgeeException):
    pass

class RemoteError(OpgeeException):
    """
    Returned when we catch any exception so it can be handled
    in the Manager.
    """
    def __init__(self, msg, field_name, trial=None):
        self.msg = msg
        self.field_name = field_name
        self.trial = trial

    def __str__(self):
        trial_str = f" trial={self.trial}" if self.trial is not None else ""
        return f"<RemoteError field='{self.field_name}'{trial_str} msg='{self.msg}'>"

class TrialErrorWrapper(OpgeeException):
    """
    Wraps an exception to add the trial number for debugging
    """
    def __init__(self, error, trial):
        self.trial = trial
        self.error = error

    def __str__(self):
        return f"trial:{self.trial} {self.error}"
