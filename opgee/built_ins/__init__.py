from .config_plugin import ConfigCommand
from .graph_plugin import GraphCommand
from .gui_plugin import GUICommand
from .run_plugin import RunCommand
from .csv2xml_plugin import XmlCommand
from .merge_plugin import MergeCommand

BuiltinSubcommands = [ConfigCommand, GraphCommand, GUICommand, MergeCommand, RunCommand, XmlCommand]
