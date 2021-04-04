from .config_plugin import ConfigCommand
from .new_plugin import NewProjectCommand
from .run_plugin import RunCommand
from .xml_plugin import XmlCommand

BuiltinSubcommands = [ConfigCommand, NewProjectCommand, RunCommand, XmlCommand]
