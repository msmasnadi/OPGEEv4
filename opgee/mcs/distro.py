# Created on Mar 20, 2012
# Incorporated into pygcam (2015)
# Incorporated into OPGEE (2022)
#
# @author: Rich Plevin
# @author: Sam Fendell
#
# Copyright (c) the authors, 2012-2022.
# See the https://opensource.org/licenses/MIT for license details.
#
import inspect
import math
import os
import re

import numpy as np
from scipy.stats import lognorm, triang, uniform, norm, rv_discrete, truncnorm

from ..error import OpgeeException, DistributionSpecError, McsUserError
from ..log import getLogger
from ..pkg_utils import resourceStream

_logger = getLogger(__name__)


def parseDistroKey(key):
    '''
    Gets the name and list of dimensions from a distro key. Inverse of makeDistroKey
    '''
    s = re.split(r'\[', key)
    return s[0], s[1][:-1].split(',')

def makeDistroKey(name, dimensions, dropZeros=False):
    '''
    Generate a dictionary key for the variable and a list of dimension indices.
    This is a normal function because it is used by both the MatrixRV
    and ParameterSet classes. Inverse of parseDistroKey.
    '''
    if not dimensions:
        return name

    if dropZeros and all(dim == 0 for dim in dimensions):
        return name

    distroKey = name + re.sub(r'[\s\']', r'', str(dimensions))
    return distroKey

# For debugging only
def dumpDistros(distroDict):
    for key in sorted(distroDict.iterkeys()):
        subDistroDict = distroDict[key]
        for d in subDistroDict.values():
            _logger.info(d)

def uniformMinMax(min, max):
    return uniform(loc=min, scale=(max - min))

def uniformRange(range):
    if range <= 0.0:
        raise OpgeeException("Uniform range must be > 0.0; %f was given" % range)

    return uniformMinMax(-range, range)

def uniformFactor(factor):
    if factor < 0.0 or factor > 1.0:
        raise OpgeeException("Uniform factor must be between 0.0 and 1.0; %f was given" % factor)

    return uniformMinMax(1 - factor, 1 + factor)

def uniformLogfactor(logfactor):
    if logfactor < 1.0:
        raise OpgeeException("Uniform logfactor must be > 1.0; %f was given" % logfactor)

    return uniformMinMax(1.0/logfactor, logfactor)

#
# Various ways to specify a lognormal random variable:
#
def lognormalRvForNormal(mu, sigma):
    '''
    Define a lognormal RV by the mean and stdev of the underlying Normal distribution
    '''
    return lognorm(sigma, scale=math.exp(mu))

def lognormalRv(logMean, logStd):
    '''
    Define a lognormal RV by its own mean and stdev
    '''
    logVar = float(logStd) ** 2
    mSqrd = float(logMean) ** 2
    mu = math.log(mSqrd / math.sqrt(logVar + mSqrd))
    sigma = math.sqrt(math.log(logVar / mSqrd + 1))
    return lognormalRvForNormal(mu, sigma)

# TBD: poorly documented... is this the 95% CI (2.5% to 97.5%?) or the 90% CI (5% to 95%)?
def lognormalRvFor95th(lo, hi):
    '''
    Define a lognormal RV by its 95% CI.
    '''
    lo = math.log(float(lo))
    hi = math.log(float(hi))
    mu = (lo + hi) / 2.0
    sigma = (hi - mu) / 1.96  # 95th percentile of normal is (+/- 1.96) * sigma
    return lognormalRvForNormal(mu, sigma)

# TBD: UNTESTED!
def lognormalRvForIQR(q1, q3):
    '''
    Define a lognormal RV by its Q1 and Q3 values
    '''
    q1 = math.log(float(q1))
    q3 = math.log(float(q3))
    mu = (q1 + q3) / 2.0
    iqr = q3 - q1
    sigma = iqr / 1.34896
    return lognormalRvForNormal(mu, sigma)

def logfactor(factor):
    """
    Define a lognormal distribution assuming the 2.5% and 97.5% values
    are 1/factor and factor, respectively.
    """
    if factor < 1.0:
        raise OpgeeException("LogFactor 'factor' must be >= 1; a value of %f was given." % factor)

    return lognormalRvFor95th(1 / factor, factor)

class truncated_lognormal():
    def __init__(self, logmean, logstdev, low, high):
        self.logmean = logmean
        self.logstdev = logstdev
        self.low = low
        self.high = high

        self.rv = lognormalRv(logmean, logstdev)

    def ppf(self, q):
        y = self.rv.ppf(q)

        # simple truncation of values below low to low, above high to high
        y[ y < self.low ] = self.low
        y[ y > self.high] = self.high

        return y

def triangle(min, mode, max):  # @ReservedAssignment
    # correct ordering if necessary
    if min > max:
        tmp = min
        min = max
        max = tmp

    scale = max - min
    if scale == 0:
        raise OpgeeException("Scale of triangle distribution is zero")

    c = (mode - min) / scale  # central value (mode) of the triangle
    return triang(c, loc=min, scale=scale)

def triangleRange(range):
    if range <= 0.0:
        raise OpgeeException("Triangle range must be between > 0.0; %f was given" % range)

    return triangle(-range, 0, range)

def triangleFactor(factor):
    if factor < 0.0 or factor > 1.0:
        raise OpgeeException("Triangle factor must be between 0.0 and 1.0; %f was given" % factor)

    return triangle(1 - factor, 1, 1 + factor)

def triangleLogfactor(logfactor):
    if logfactor < 1.0:
        raise OpgeeException("Triangle logfactor must be > 1.0; %f was given" % logfactor)

    return triangle(1.0/logfactor, 1, logfactor)

def binary():
    return rv_discrete(name="binary", values=[(0, 1), (0.5, 0.5)])

def weighted_binary(prob_of_one):
    return rv_discrete(name="weighted_binary", values=[(0, 1), (1-prob_of_one, prob_of_one)])

def integers(min, max):
    min = int(min)
    max = int(max)
    count = max - min + 1
    nums  = list(range(min, max + 1))
    probs = [1.0/count] * count
    return rv_discrete(name='integers', values=[nums, probs])


class truncated_normal():
    def __init__(self, mean, stdev, low, high):
        self.mean = mean
        self.stdev = stdev
        self.low = low
        self.high = high

        # Get a and b parameters for truncated standard normal distribution
        # See https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.truncnorm.html
        a, b = (low - mean) / stdev, (high - mean) / stdev
        self.rv = truncnorm(a, b)

    def ppf(self, q):
        y = self.rv.ppf(q)
        # shift standard normal back to original shape and location
        shifted = y * self.stdev + self.mean
        return shifted

class constant():
    """
    Return an object that produces an array holding the given
    constant value. Useful for forcing a parameter to a given value.
    """
    def __init__(self, value):
        self.value = value

    def ppf(self, q):
        n = np.ndarray(len(q))
        n[:] = self.value
        return n

class sequence():
    """
    Return an object that produces an array holding the given sequence
    of constant values. Useful for forcing parameters to given values.
    """
    def __init__(self, values):
        self.values = [float(item) for item in values.split(',')]

    def ppf(self, q):
        n = len(q)  # length of array to return
        count = len(self.values)    # items in the sequence

        seq = ((int(n / count) + (1 if n % count else 0)) * self.values)

        # truncate in case n wasn't a multiple of count
        arr = np.array(seq[:n])
        return arr

class Empirical():
    """
    Create an empirical distribution and ppf from an array of observations.
    """
    file_cache = {}     # maps pathname of CSV file to dataframe

    def __init__(self, values):
        self.values = sorted(values)
        self.count = len(values)

    def ppf(self, q):
        values = self.values
        n = len(values)
        result = [values[int(n * percentile)] for percentile in q]
        return result

    @classmethod
    def from_csv(cls, pathname=None, colname=None): # both are required args, but must be keywords to use with DistroGen.makeRV()
        import pandas as pd

        df = cls.file_cache.get(pathname)

        if df is None:
            try:
                csvdata = pathname if os.path.isabs(pathname) else resourceStream(pathname, stream_type='bytes', decode=None)
                df = pd.read_csv(csvdata, index_col=False)
            except Exception as e:
                raise McsUserError(f"from_csv: Unable to read empirical data file '{pathname}': {e}")

            cls.file_cache[pathname] = df

        if colname not in df.columns:
            raise McsUserError(f"from_csv: Column '{colname}' not found in '{pathname}'")

        values = df[colname]
        return cls(values)

    @classmethod
    def clear_file_cache(cls):
        cls.file_cache.clear()

class GridRV(object):
    '''
    Return an object that behaves like an RV in that it returns N values when
    when requested via the ppf (percent point function), though the N values are
    merely a shuffled sequence of a "gridded" range repeated to produce N values.
    No other methods of the standard RV class are implemented. This is intended
    for use in CoreMCS and derivatives only.
    '''
    def __init__(self, min, max, count):
        self.values = np.linspace(min, max, count)
        _logger.debug("Generated values: %s", self.values)


    def ppf(self, q):
        '''
        Return 'n' values from this object's list of values, repeating those values
        as many times as necessary to produce 'n' values, where 'n' is the length of
        the percentile list given by 'q'. (We ignore the values, though.)
        '''
        n = len(q)
        values = self.values
        assert len(values.shape) == 1, "Grid values were converted to ndarray of > 1 dimension"
        count  = values.shape[0]
        reps   = 1 if n <= count else np.ceil(float(n) / count)
        tiled  = np.tile(values, reps)[:n]
        np.random.shuffle(tiled)                # TBD: might be redundant as shuffle is called from LHS
        # _logger.debug("tiled=%s", tiled)
        return tiled

class linkedDistro(object):
    def __init__(self, parameter):
        '''Linked to (i.e., shares RV data with) `withParameter`'''
        self.parameter = parameter

    # this is needed to handle linked parameters
    trialData = None

    @classmethod
    def storeTrialData(cls, df):
        cls.trialData = df

    @classmethod
    def getTrialData(cls):
        return cls.trialData

    def ppf(self, q):
        return self.trialData[self.parameter]    # TBD: return as an ndarray

class DistroGen(object):
    '''
    Stores information required to generate a Distro instance from an argDict
    '''
    instances = {}    # Store a dict of our instances internally

    def __init__(self, distName, func):
        self.name = distName
        self.func = func
        self.sig  = DistroGen.signature(distName, inspect.signature(func).parameters)
        DistroGen.instances[self.sig] = self

    def __str__(self):
        classname = type(self).__name__
        _logger.debug("<%s dist=%s func=%s sig=%s>", classname, self.name, self.func, self.sig)

    @classmethod
    def signature(cls, distName, keywords):
        '''
        Makes a unique signature for a distribution type out of its name
        and a collection of argument names.
        '''
        lst = list(keywords)
        lst.append('#' + distName.lower())  # assures that distname doesn't overlap with any of the argument names
        return frozenset(lst)

    @classmethod
    def generator(cls, sig):
        cls.genDistros()
        return cls.instances.get(sig, None)

    def makeRV(self, argDict):
        'Call the generator function with an argDict to create a frozen RV'
        return self.func(**argDict)

    @classmethod
    def genDistros(cls):
        '''
        Generate a basic set of distributions
        '''
        if cls.instances:
            return

        cls('uniform', uniformMinMax)

        # range=0.2 means a Uniform(min=-0.2, max=0.2); used with apply="add"
        cls('uniform', uniformRange)

        # factor=0.2 means Uniform(min=0.8, max=1.2); used with apply="multiply"
        cls('uniform', uniformFactor)

        # logfactor=3 means Uniform(1/3, 3); used with apply="multiply"
        cls('uniform', uniformLogfactor)

        cls('weighted_binary', weighted_binary)

        # LogUniform distribution from 1/n to n, e.g., factor=3 => uniform(1/3, 3)
        cls('loguniform', lambda factor: uniformMinMax(min=1 / factor, max=factor))

        cls('normal', lambda mean, std: norm(loc=mean, scale=std))
        cls('normal', lambda mean, stdev: norm(loc=mean, scale=stdev))          # alternate spelling

        cls('lognormal', lambda logmean, logstdev: lognormalRv(logmean, logstdev))
        cls('lognormal', lambda mean, stdev: lognormalRvForNormal(mean, stdev))
        cls('lognormal', lambda low95, high95: lognormalRvFor95th(low95, high95))
        cls('lognormal', logfactor)

        cls('truncated_lognormal', truncated_lognormal)

        # range=0.2 means a triangle with min, mode, max = (-0.2, 0, +0.2); for apply="add"
        cls('triangle', triangleRange)    # args: range (must be > 0)

        # factor=0.2 means triangle with min, mode, max = (0.8, 1, 1.2); for apply="multiply"
        cls('triangle', triangleFactor)    # args: factor: must be > 0 and < 1

        # logfactor=3 means triangle with min, mode, max = (1/3, 1, 3); for apply="multiply"
        cls('triangle', triangleLogfactor)    # args: logfactor: must be > 1

        cls('triangle', triangle)         # args: min, mode, max

        cls('truncated_normal', truncated_normal)

        cls('binary', binary)
        cls('integers', integers)     # args: min, max (inclusive)

        # Gridded (non-random) sequence.
        # Returns a frozen RV-like object with a "ppf" method that returns a sequence of values
        # produced by cycling through 'count' values evenly spaced starting at 'min' and ending
        # at 'max'.
        cls('grid', lambda min, max, count: GridRV(min, max, count))

        cls('constant', lambda value: constant(value))

        cls('sequence', lambda values: sequence(values))

        cls('linked', lambda parameter: linkedDistro(parameter)),

        cls('empirical', Empirical.from_csv)




def get_frozen_rv(distro_name, **kwargs):
    sig = DistroGen.signature(distro_name, kwargs.keys())
    gen = DistroGen.generator(sig)

    if gen is None:
        raise DistributionSpecError(f"Unknown distribution signature {sig}")

    rv = gen.makeRV(kwargs)  # generate a frozen RV with the specified arguments
    return rv
