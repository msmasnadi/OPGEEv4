from .core import Process
from .log import getLogger

_logger = getLogger(__name__)

#
# Processes from OPGEEv3 workbook
#
class Exploration(Process):
    pass

class FieldDevelopment(Process):
    pass

class Fracking(Process):
    pass

class FluidProduction(Process):
    pass

class FluidInjection(Process):
    pass

class BitumenMining(Process):
    pass

class Maintenance(Process):
    pass

class CrudeSeparationAndHandling(Process):
    pass

class CrudeStorage(Process):
    pass

class BitumenUpgradingOrDistilation(Process):
    pass

class WasteTreatmentAndDisposal(Process):
    pass

class CrudeTransport(Process):
    pass
