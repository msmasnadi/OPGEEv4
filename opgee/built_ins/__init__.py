from .config_plugin import ConfigCommand
from .graph_plugin import GraphCommand
from .run_plugin import RunCommand
from .xml_plugin import XmlCommand

BuiltinSubcommands = [ConfigCommand, GraphCommand, RunCommand, XmlCommand]
