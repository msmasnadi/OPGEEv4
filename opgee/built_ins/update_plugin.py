#
# Author: Richard Plevin
#
# Copyright (c) 2023 the author and The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..log import getLogger
from ..subcommand import SubcommandABC

_logger = getLogger(__name__)

class UpdateCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : 'Update model XML files with Fields inside Analyses to use FieldRef instead.'}
        super().__init__('update', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('model_file',
                            help='''The model XML file to operate on.''')

        parser.add_argument('-o', '--output',
                            help='''The path of the updated model XML file. If not specified, 
                            the output name will be the input name with "-updated" added before 
                            the ".xml" extension.''')

        parser.add_argument('--overwrite', action='store_true',
                            help='Force overwrite of an existing model XML. Cannot be the same'
                                 'file as the input.')

        parser.add_argument('--ignore-duplicates', action='store_true',
                            help='Ignore duplicate field names in the input file, saving only the final one.')

        return parser   # used for auto-doc generation


    def run(self, args, tool):
        from collections import OrderedDict
        import os
        from lxml import etree as ET
        from opgee.error import CommandlineError, XmlFormatError
        from opgee.XMLFile import XMLFile

        input = args.model_file
        if not os.path.isfile(input):
            raise CommandlineError(f"Specified model XML file '{input}' does not exist.")

        output = args.output
        if not output:
            dirs, filename = os.path.split(input)
            basename, ext = os.path.splitext(filename)
            output = os.path.join(dirs, f"{basename}-updated{ext}")

        print(f"Updating model XML file '{input}' to '{output}'")

        if os.path.lexists(output):
            if os.path.samefile(input, output):
                raise CommandlineError("Input and output cannot be the same file.")

            if not args.overwrite:
                raise CommandlineError(f"Specified output XML file '{output}' exists. Use --overwrite to overwrite.")

        xmlfile = XMLFile(input)
        root = xmlfile.getRoot()

        field_dict = OrderedDict()
        # analyses = root.findall('Analysis')
        for analysis in root.iter('Analysis'):
            for field in analysis.iter('Field'):
                name = field.attrib['name']

                if field_dict.get(name) and not args.ignore_duplicates:
                    raise XmlFormatError(f"Field '{name}' appears multiple times in file '{input}'. "
                                         "Use --ignore-duplicates to save only the final <Field> element.")

                field_dict[name] = field

                # replace <Field> element with <FieldRef>
                analysis.remove(field)
                ET.SubElement(analysis, 'FieldRef', attrib={'name': name})

        # Move all <Field> elements to the <Model> root
        for field in field_dict.values():
            root.append(field)

        print(f"Writing '{output}'")
        tree = xmlfile.getTree()
        tree.write(output, xml_declaration=True, pretty_print=True, encoding='utf-8')
