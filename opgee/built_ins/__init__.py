from .config_plugin import ConfigCommand
from .graph_plugin import GraphCommand
from .new_plugin import NewProjectCommand
from .run_plugin import RunCommand
from .xml_plugin import XmlCommand

BuiltinSubcommands = [ConfigCommand, GraphCommand, NewProjectCommand, RunCommand, XmlCommand]
