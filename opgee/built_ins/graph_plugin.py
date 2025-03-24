"""
.. Graph aspects of OPGEE models (class hierary, model structure)

.. codeauthor:: <rich@plevin.com>

.. Copyright (c) 2021  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from ..subcommand import SubcommandABC, clean_help
from ..log import getLogger

_logger = getLogger(__name__)

class GraphCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Create graphs of various aspects of OPGEE models.'''}
        super().__init__('graph', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        from ..utils import ParseCommaList

        class_choices = ['all', 'core']
        parser.add_argument('-c', '--classes', choices=class_choices,
                            help=clean_help('''Graph the class structure, either "all", including all defined
                            Process subclasses (of which there are dozens) or only the "core" classes excluding
                            Process subclasses.'''))

        parser.add_argument('-C', '--classes-output',
                            help=clean_help('''The pathname of the image file to create for classes. If none 
                            is specified, and the code is running in a jupyter notebook, the image is 
                            displayed inline. (Implies --classes.)'''))

        parser.add_argument('-e', '--exclude-classes', action=ParseCommaList,
                            help=clean_help('''Classes to exclude from graph creation when using --classes-output.'''))

        parser.add_argument('-f', '--field',
                            help=clean_help('''Graph the process network for the named field.'''))

        parser.add_argument('-F', '--field-output',
                            help=clean_help('''The pathname of the image file to create with process connections
                            for the field specified in the --field argument. If no file is specified, and the code
                            is running in a jupyter notebook, the image is displayed inline.'''))

        parser.add_argument('-l', '--levels', type=int, default=0,
                            help=clean_help('''How many levels to descend when graphing the model hierarchy'''))

        parser.add_argument('-m', '--model-hierarchy', action='store_true',
                            help=clean_help('''Graph the model container hierarchy.'''))

        parser.add_argument('-M', '--hierarchy-output',
                            help=clean_help('''The pathname of the image file to create for classes. If none 
                            is specified, and the code is running in a jupyter notebook, the image is 
                            displayed inline. (Implies --model_hierarchy.)'''))

        parser.add_argument('-n', '--no-default-model', action='store_true',
                            help=clean_help('''Don't load the built-in opgee.xml model definition.'''))

        parser.add_argument('-x', '--xml_file', default=None,
                            help="""The path to the model XML file to load. By default, the built-in opgee.xml is loaded.""")
        return parser

    def run(self, args, tool):
        from ..error import CommandlineError
        from ..graph import write_model_diagram, write_class_diagram, write_process_diagram
        from ..model_file import ModelFile

        use_default_model = not args.no_default_model
        mf = ModelFile(args.xml_file, use_default_model=use_default_model)

        model = mf.model

        if args.model_hierarchy or args.hierarchy_output:
            write_model_diagram(model, args.hierarchy_output, levels=args.levels)

        if args.classes or args.classes_output:
            show_process_subclasses = (args.classes == 'all')
            write_class_diagram(args.classes_output,
                                show_process_subclasses=show_process_subclasses,
                                exclude=args.exclude_classes)

        if args.field:
            field = model.field_dict.get(args.field)

            if not field:
                raise CommandlineError(f"Field name {args.field} was not found in model.")

            write_process_diagram(field, args.field_output)
