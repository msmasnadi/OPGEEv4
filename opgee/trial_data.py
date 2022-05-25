#
# Created as part of pygcam (2015)
# Adapted for use in OPGEE (2022)
#
# Copyright (c) Richard Plevin, 2012-2022.
# See the https://opensource.org/licenses/MIT for license details.
#
from collections import OrderedDict, defaultdict
from math import ceil
import numpy as np
import os

from .config import getParam
from .core import OpgeeObject
from .distro import DistroGen
from .error import OpgeeException
from .log import getLogger

_logger = getLogger(__name__)

class McsUserError(OpgeeException):
    pass

class McsSystemError(OpgeeException):
    pass

class DistributionSpecError(OpgeeException):
    pass


class TrialData(OpgeeObject):
    """
    An abstract class that provides the protocol required of classes that can produce
    trial data, i.e., XMLDistribution, DataFile, or PythonFunc
    """
    def __init__(self, param, apply=None):
        super(TrialData, self).__init__()
        self.param = param
        self.rv    = None
        self.apply = apply or 'replace'  # if not specified, we'll replace default value

    def getMode(self):
        """
        Get the containing parameter mode, one of {'direct', 'shared', 'independent'}
        """
        return self.param.getMode()

    def isShared(self, mode=None):
        mode = mode or self.getMode()
        return mode == 'shared'

    def isDirect(self, applyAs=None):
        applyAs = applyAs or self.apply
        return applyAs == 'replace'

    def isFactor(self, applyAs=None):
        applyAs = applyAs or self.apply
        return applyAs in ('mult', 'multiply')

    def isDelta(self, applyAs=None):
        applyAs = applyAs or self.apply
        return applyAs == 'add'

    def isTrialFunc(self):      # overridden in XMLDistribution when apply is a func reference
        return False

    def isLinked(self):         # overridden in XMLDistribution
        return False

    def ppf(self, *args):
        cls_name = self.__class__.name
        raise McsSystemError(f"Called abstract 'ppf' method of {cls_name}")


class XMLDistribution(TrialData):
    """
    A wrapper around a <Distribution> element to provide some
    convenience functions.
    """
    trialFuncDir = None

    @classmethod
    def decache(cls):
        cls.trialFuncDir = None

    def __init__(self, element, param):
        super(XMLDistribution, self).__init__(element, param)

        self.argDict  = {}
        self.modDict = defaultdict(lambda: None)
        self.modDict['apply'] = 'direct'    # set default value

        # Deprecated for opgee?
        # # Distribution attributes are {apply, highbound, lowbound}, enforced by XSD file
        # for key, val in element.items():
        #     self.modDict[key] = val

        # Load trial function, if defined (i.e., if there's a '.' in the value of the "apply" attribute.)
        self.trialFunc = self.loadTrialFunc()

        self.otherArgs = None
        if self.trialFunc:
            elt = self.element.find('OtherArgs')
            if elt is not None and elt.text:
                codeStr = "dict({})".format(elt.text)
                try:
                    self.otherArgs = eval(codeStr)

                except SyntaxError as e:
                    raise DistributionSpecError(f"Failed to evaluate expression {codeStr}: {e}")

        self.child = element[0]
        self.distroName = self.child.tag.lower()

        # TBD: hack alert to deal with non-float attribute. Fix this in the rewrite.
        # TBD: Might be cleaner to have something that isn't confused with a distribution?
        self._isLinked = self.child.tag == 'Linked'
        if self._isLinked:
            attr = 'parameter'
            self.argDict[attr] = self.child.get(attr)

        elif self.distroName == 'sequence':
            for key, val in self.child.items():
                self.argDict[key] = val           # don't convert to float

        else:
            for key, val in self.child.items():
                self.argDict[key] = float(val)    # these form the signature that identifies the distroElt function

        sig = DistroGen.signature(self.distroName, self.argDict.keys())
        _logger.debug("<Distribution %s, %s>", ' '.join(map(lambda pair: '%s="%s"' % pair, element.items())), sig)

        gen = DistroGen.generator(sig)
        if gen is None:
            raise DistributionSpecError("Unknown distribution signature %s" % str(sig))

        self.rv = gen.makeRV(self.argDict)  # generate a frozen RV with the specified arguments

    def getKeys(self):
        return self.child.keys()

    def isTrialFunc(self):
        return bool(self.trialFunc)

    def isLinked(self):
        return self._isLinked

    def linkedParameter(self):
        return self.argDict['parameter'] if self._isLinked else None

    def ppf(self, *args):
        """
        ppf() takes a first arg that can be a scalar value (percentile) or a list
        of percentiles, which is how we use it in this application.
        """
        return self.rv.ppf(*args)

    def loadTrialFunc(self):

        funcRef = self.modDict['apply']
        if not '.' in funcRef:
            return None

        if not self.trialFuncDir:
            self.trialFuncDir = getParam('MCS.TrialFuncDir')

        modname, objname = funcRef.rsplit('.', 1)
        modulePath = os.path.join(self.trialFuncDir, modname + '.py')
        try:
            trialFunc = loadObjectFromPath(objname, modulePath)
        except Exception as e:
            raise McsUserError("Failed to load trial function '{}': {}".format(funcRef, e))

        return trialFunc

class PythonFunc(TrialData):
    """
    Implements user-defined Python function to be called to generate a series of
    values. The func can access parameters by calling XMLParameter.getInstances(),
    or XMLParameter.getInstance(name) to get one by name.

    The XMLSchema ensures the format is pkg.mod.submod.func or a legal variant.
    """
    def __init__(self, element, param):
        super(PythonFunc, self).__init__(element, param)
        self.func = importFromDotSpec(element.text)

    def ppf(self, *args):
        """
        Call the function specified in the XML file, passing in the arguments to
        the ppf(), which should be a list of percentile values for which to return
        values from whatever underlies this Python function.

        :param args: the list of percentile values for which to return values. These
          can be ignored, e.g., if the function computes some values based on other
          trial data.
        :return: array-like
        """
        return self.func(self.param, *args)


class DataFile(TrialData):
    """
    Holds DataFrames representing files already loaded, keyed by abs pathname.
    A single data file can hold vectors of values for multiple Parameters; this
    way the file is loaded only once. This can be used to load pre-generated
    trial data, e.g. exported from other software.
    """
    cache = OrderedDict()

    @classmethod
    def getData(cls, pathname):
        """
        Return the DataFrame created by loading the file at pathname. Read the
        file if it's not already in the cache, otherwise, just return the stored DF.
        """
        import pandas as pd

        pathname = os.path.abspath(pathname)    # use canonical name for cache

        if pathname in cls.cache:
            return cls.cache[pathname]

        df = pd.read_table(pathname, sep='\t', index_col=0)
        df.reset_index(inplace=True)
        cls.cache[pathname] = df
        return df

    @classmethod
    def decache(cls):
        cls.cache = OrderedDict()

    def __init__(self, element, param):
        super(DataFile, self).__init__(element, param)
        filename = self.getFilename()
        self.df  = self.getData(filename)

    def getFilename(self):
        return os.path.expanduser(self.element.text)

    def ppf(self, *args):
        'Pseudo-ppf that just returns a column of data from the cached dataframe.'
        name   = self.param.getName()
        count  = len(args[0])

        if name not in self.df:
            raise McsUserError("Variable '%s' was not found in '%s'" % self.getFilename())

        vector = self.df[name]

        if len(vector) < count:
            # get the smallest integer number of repeats of the
            # vector to meet or exceed the desired count
            repeats = int(ceil(float(count)/len(vector)))
            vector  = np.array(list(vector) * repeats)

        return vector[:count]


class Variable(OpgeeObject):
    """
    Simple variable that wraps an Element and provides methods to get, set,
    cache, and restore Element values. This is subclassed by RandomVariable
    to provide a ppf() function for generating samples.
    """
    def __init__(self, element, param, varNum=None):
        super(Variable, self).__init__(element)
        self.param       = param
        self.paramPath   = None
        self.storedValue = None      # cached float value

        # N.B. "is not None" is required because "not element" isn't guaranteed to work.
        if element is not None:      # For shared RVs, XMLParameter creates RandomVariable with element=None
            self.storeFloatValue()   # We refer to stored value when updating the XML tree for each trial

        # Save the column in the trailMatrix with our values. This is passed
        # in when Variables are instantiated directly (for shared variables)
        # and set automatically during initialization of RandomVariableiables.
        self.varNum = varNum

    def getParameter(self):
        return self.param

    def getVarNum(self):
        return self.varNum

    def setVarNum(self, varNum):
        self.varNum = varNum

    def getValue(self):
        return self.element.text

    def setValue(self, value):
        """
        Set the value of the element stored in an Variable.
        """
        elt = self.getElement()
        elt.text = str(value)

    def storeFloatValue(self):
        """
        Store the current value as a float
        """
        value = self.getValue()
        try:
            self.storedValue = float(value)
        except Exception:
            name = self.param.getName()
            raise McsSystemError("Value '%s' for parameter %s is not a float" % (value, name))

    def getFloatValue(self):
        return self.storedValue


class RandomVariable(Variable):
    """
    Stores pointer to an XMLDistribution (unless this is a shared RV).
    Provides access to values by trial number via valueFunc.
    """
    instances = []

    @classmethod
    def saveInstance(cls, obj):
        # Our position in the RV list identifies our column in the trial matrix
        obj.setVarNum(len(cls.instances))
        cls.instances.append(obj)

    @classmethod
    def getInstances(cls):
        return cls.instances

    @classmethod
    def decache(cls):
        cls.instances = []

    def __init__(self, element, param):
        super(RandomVariable, self).__init__(element, param)
        self.saveInstance(self)

    def ppf(self, *args):
        """
        Pass-thru to the Distribution's ppf() method. Called by LHS.
        """
        dataSrc = self.param.getDataSrc()
        if not dataSrc:
            raise McsUserError("Called ppf on shared RandomVariable (dataSrc is None)")

        return dataSrc.ppf(*args)
