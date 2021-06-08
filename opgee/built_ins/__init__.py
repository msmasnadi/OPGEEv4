from .config_plugin import ConfigCommand
from .graph_plugin import GraphCommand
from .gui_plugin import GUICommand
from .run_plugin import RunCommand
from .xml_plugin import XmlCommand

BuiltinSubcommands = [ConfigCommand, GraphCommand, GUICommand, RunCommand, XmlCommand]
