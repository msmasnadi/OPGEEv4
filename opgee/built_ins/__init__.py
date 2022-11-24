from .compare_plugin import CompareCommand
from .config_plugin import ConfigCommand
from .graph_plugin import GraphCommand
from .gui_plugin import GUICommand
from .run_plugin import RunCommand
from .csv2xml_plugin import Csv2XmlCommand
#from .launch_plugin import LaunchCommand
from .merge_plugin import MergeCommand
from .gensim_plugin import GensimCommand
from .ippsetup_plugin import IppSetupCommand
# from .ray_plugin import RayCommand
from .runsim_plugin import RunsimCommand
#from .genwor_plugin import GenworCommand

BuiltinSubcommands = [
    CompareCommand,
    ConfigCommand,
    Csv2XmlCommand,
    GensimCommand,
    # GenworCommand
    GraphCommand,
    GUICommand,
    IppSetupCommand,
    # LaunchCommand,
    MergeCommand,
    # RayCommand,
    RunCommand,
    RunsimCommand,
]
