from .config_plugin import ConfigCommand
from .graph_plugin import GraphCommand
from .gui_plugin import GUICommand
from .run_plugin import RunCommand
from .csv2xml_plugin import XmlCommand
from .merge_plugin import MergeCommand
from .gensim_plugin import GensimCommand
from .runsim_plugin import RunsimCommand
from .genwor_plugin import GenworCommand

BuiltinSubcommands = [
    ConfigCommand, GraphCommand, GensimCommand, GenworCommand, GUICommand,
    MergeCommand, RunCommand, RunsimCommand, XmlCommand
]
