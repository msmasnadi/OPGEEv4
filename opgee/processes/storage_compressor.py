import math

from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID, PHASE_GAS
from opgee.stream import Stream
from ..config import getParam
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
from .. import ureg
from ..compressor import Compressor
from ..energy import Energy, EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
from ..emissions import Emissions, EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES

_logger = getLogger(__name__)


class StorageCompressor(Process):
    """
    Storage compressor calculate emission from compressing gas for long-term (i.e., seasonal) storage

    """

    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas