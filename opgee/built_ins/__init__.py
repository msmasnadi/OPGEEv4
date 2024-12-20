from .collect_plugin import CollectCommand
from .compare_plugin import CompareCommand
from .config_plugin import ConfigCommand
from .graph_plugin import GraphCommand
from .gui_plugin import GUICommand
from .run_plugin import RunCommand
from .csv2xml_plugin import Csv2XmlCommand
from .merge_plugin import MergeCommand
from .gensim_plugin import GensimCommand
from .update_plugin import UpdateCommand

BuiltinSubcommands = [
    CollectCommand,
    CompareCommand,
    ConfigCommand,
    Csv2XmlCommand,
    GensimCommand,
    GraphCommand,
    GUICommand,
    MergeCommand,
    RunCommand,
    UpdateCommand,
]
