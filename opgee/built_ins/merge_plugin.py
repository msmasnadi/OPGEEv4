"""
.. Merge two or more OPGEE XML files. Mainly for testing merge code, but may be useful otherwise.

.. codeauthor:: <rich@plevin.com>

.. Copyright (c) 2021,2022  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from pathlib import Path
from ..subcommand import SubcommandABC
from ..log import getLogger

_logger = getLogger(__name__)


class MergeCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Merge two or more OPGEE XML files.'''}
        super().__init__('merge', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        parser.add_argument('pathnames', nargs='*',
                            help="""Pathnames of the XML input files to be merged, in the order specified. By default,
                                 the built-in {opgee}/etc/opgee.xml is included as the base file to merge with. To 
                                 override this, use the -n/--no-default-model option.""")

        parser.add_argument('-o', '--outputXML', default=None,
                            help='''The pathname of the XML file to create. Default is the same
                            name as the input CSV file, but with the extension changed to "xml". Refuses
                            to overwrite an existing file unless --overwrite is specified. If an output
                            XML file is not specified, the merged XML is written to stdout.''')

        parser.add_argument('-n', '--no-default-model', action='store_true',
                            help='''Don't use the built-in {opgee}/etc/opgee.xml model file as the base 
                                    file to merge with.''')

        parser.add_argument('--overwrite', action='store_true',
                            help='''If set, allows existing XML file to be overwritten.''')

        return parser

    def run(self, args, tool):
        from ..error import CommandlineError
        from ..model_file import ModelFile

        pathnames = args.pathnames
        if not pathnames:
            raise CommandlineError('Missing required input XML file(s)')

        if args.outputXML:
            output_path = Path(args.outputXML)

            if output_path.exists() and not args.overwrite:
                raise CommandlineError(f"Refusing to overwrite '{output_path}'; use --overwrite to override this.")

            # etree write fn can take pathname (str) or file descriptor, but not Path()
            output_path = str(output_path)
        else:
            output_path = None

        use_default_model = not args.no_default_model
        mf = ModelFile(pathnames, use_default_model=use_default_model,
                       instantiate_model=False, save_to_path=output_path)

        if not output_path:
            from lxml import etree
            etree.dump(mf.root, pretty_print=True)
