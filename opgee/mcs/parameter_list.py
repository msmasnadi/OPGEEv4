from ..config import getParam
from ..core import OpgeeObject
from ..error import McsSystemError
from ..log import getLogger
from ..pkg_utils import resourceStream
from ..utils import getBooleanXML
from ..XMLFile import XMLFile
from .distro import get_frozen_rv

_logger = getLogger(__name__)


DISTROS_XML = 'mcs/etc/parameter-distributions.xml'

class ParameterList(XMLFile):
    def __init__(self, filename, xml_string=None):
        super().__init__(filename,
                         schemaPath='mcs/etc/parameter-schema.xsd',
                         xml_string=xml_string,
                         removeComments=True,
                         conditionalXML=False)

        root = self.getRoot()
        params = [Parameter(elt) for elt in root.findall('Parameter')]
        self.parameter_dict = {p.name : p for p in params if p.active}

    @classmethod
    def load(cls, pathname=None, xml_string=None):
        """
        Read distributions from the designated XML file. The default is to use
        the file indicated by configuration parameter OPGEE.DistributionFile, which
        defaults to the built-in file opgee/mcs/etc/parameter-distributions.xml.

        :param pathname: (str) the pathname of the XML file describing distributions
        :param xml_string: (str) text representation of XML to use instead of ``pathname``.
        :return: (ParameterList) a populated ``ParameterList`` instance
        """
        if xml_string:
            distros_xml = None
        else:
            default_path = getParam('OPGEE.DistributionFile')
            distros_xml = pathname or resourceStream(default_path,
                                                     stream_type="bytes",
                                                     decode=None)

        return ParameterList(distros_xml, xml_string=xml_string)

    def parameter(self, name):
        return self.parameter_dict.get(name)

    def parameters(self):
        """
        Return a list of the defined Parameter instances.

        :return: (list of Parameter) the instances
        """
        return self.parameter_dict.values()


class Parameter(OpgeeObject):
    def __init__(self, elt):
        self.name = elt.attrib['name']
        self.active = getBooleanXML(elt.attrib.get('active', '1'))
        self.shape = None
        distro = elt.find('Distribution')
        self.rv = self.create_rv(distro) if self.active else None

    def __str__(self):
        return f"""<Parameter name:{self.name} shape:{self.shape}>"""

    def create_rv(self, distro_elt):
        name = self.name

        child = distro_elt[0]       # schema ensures only one sub-element
        self.shape = shape = child.tag
        attrib = child.attrib

        def number(name, default=None):
            s = attrib.get(name)
            return default if s is None else float(s)

        low = number('min')
        high = number('max')
        mean = number('mean')
        stdev = number('stdev')
        mode = number('mode')
        log_mean = number('log_mean')
        log_stdev = number('log_stdev')
        prob_of_yes = number('prob_of_yes', 0.5)

        # if low == '' and high == '' and mean == '' and prob_of_yes == '' and shape != 'empirical':
        #     _logger.info(f"* {name} depends on other distributions / smart defaults")        # TODO add in lookup of attribute value
        #     continue

        rv = None

        if shape == 'Binary':
            if prob_of_yes == 0 or prob_of_yes == 1:
                _logger.info(f"* Ignoring distribution on {name}, Binary distribution has prob_of_yes = {prob_of_yes}")
            else:
                rv = get_frozen_rv('weighted_binary', prob_of_one=prob_of_yes)

        elif shape == 'Uniform':
            if low == high:
                _logger.info(f"* Ignoring distribution on {name}, Uniform high and low bounds are both {low}")
            else:
                rv = get_frozen_rv('uniform', min=low, max=high)

        elif shape == 'Triangle':
            if low == high:
                _logger.info(f"* Ignoring distribution on {name}, Triangle high and low bounds are both {low}")
            else:
                rv = get_frozen_rv('triangle', min=low, mode=mode, max=high)

        elif shape == 'Normal':
            if stdev == 0.0:
                _logger.info(f"* Ignoring distribution on {name}, Normal has stdev = 0")
            else:
                if low is None or high is None:
                    rv = get_frozen_rv('normal', mean=mean, stdev=stdev)
                else:
                    rv = get_frozen_rv('truncated_normal', mean=mean, stdev=stdev, low=low, high=high)

        elif shape == 'Lognormal':
            if log_stdev == 0.0:
                _logger.info(f"* Ignoring distribution on {name}, Lognormal has stdev = 0")
            else:
                if low is None or high is None:     # must specify both low and high
                    rv = get_frozen_rv('lognormal', logmean=log_mean, logstdev=log_stdev)
                else:
                    rv = get_frozen_rv('truncated_lognormal',
                                       logmean=log_mean, logstdev=log_stdev, low=low, high=high)

        elif shape == 'Choice':
            _logger.info("* Choice distribution is not yet supported")

        elif shape == 'DataFile':
            rv = get_frozen_rv('empirical', pathname=child.text, colname=self.name)

        else:
            raise McsSystemError(f"Unknown distribution shape: '{shape}'")

        return rv
