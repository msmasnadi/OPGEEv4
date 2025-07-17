"""
.. codeauthor:: <rich@plevin.com>

.. Copyright (c) 2021  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from pathlib import Path
from ..subcommand import SubcommandABC
from ..log import getLogger

_logger = getLogger(__name__)

DEFAULT_MODIFIES = 'template'

def read_fields(csv_path, from_package=False, skip_fields=None):
    """
    Read a CSV file with attributes data for fields where columns are fields
    and rows are attributes, with the exception of one column, 'Type', which
    holds the type of the data, which must be

    :param csv_path: (str) the path to the CSV file
    :param from_package: (bool) if True, ``csv_path`` should be relative and
       is interpreted as within the opgee package.
    :param skip_fields: (list of str) the names of fields to exclude
    :return: (tuple of pd.DataFrame, pd.Series) DataFrame has attributes in columns
       and is indexed by field name. Series is indexed by attribute name holding
       the type ("str", "int", or "float") of the attribute.
    """
    import pandas as pd
    from ..pkg_utils import resourceStream

    stream = resourceStream(csv_path) if from_package else csv_path
    df = pd.read_csv(stream, index_col=0)

    # If we decide to translate attribute names here, add mappings to this dict
    v3_to_v4 = {
        'old name': 'new name',
        'old name2': 'new name2',
    }

    df.rename(index=v3_to_v4, inplace=True)

    if skip_fields:
        df.drop(skip_fields, axis='columns', inplace=True)

    # Pull dtypes out as a separate series
    dtypes = df['Type']
    df.drop('Type', axis='columns', inplace=True)

    return (df, dtypes)


def import_fields(csv_path, xml_path, analysis_name, count=0, skip_fields=None,
                  modifies=DEFAULT_MODIFIES, from_package=False, use_group=True):
    """
    Import Field information from a CSV file.

    :param csv_path: (str or Path) the CSV file to read
    :param xml_path: (str or Path) the XML file to create
    :param count: (int) if count > 0, import only the first `count` fields
    :param modifies: (str) the name of a Field the generated fields "modify"
    :param skip_fields: (list of str) the names of fields to exclude
    :param from_package: (bool) if True, treat `streams_csv_path` as relative to the
       opgee package and load the file from the internal package resource.
    :return:
    """
    from ..xml_utils import attr_to_xml

    fields, dtypes = read_fields(csv_path,
                                 from_package=from_package,
                                 skip_fields=skip_fields)

    if count:
        fields = fields[fields.columns[:count]]

    if not analysis_name:
        p = Path(csv_path)
        analysis_name = p.name[:-(len(p.suffix))]

    attr_to_xml(fields, dtypes, xml_path, analysis_name, modifies=modifies, use_group=use_group)


class Csv2XmlCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Convert various CSV files to their corresponding XML representation.'''}
        super().__init__('csv2xml', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        from ..utils import ParseCommaList

        parser.add_argument('-a', '--analysis',
                            help='''The name to give the <Analysis> element. Default is the file basename 
                            with the extension removed.''')

        default_format = 'fields'
        format_choices = [default_format, 'attributes'] # extend as needed
        parser.add_argument('-f', '--format', choices=format_choices, default=default_format,
                            help=f'''Which type of conversion to perform. Default is "{default_format}".''')

        parser.add_argument('-g', '--no_group', action='store_false', default=True, dest='use_group',
                            help='''Use <FieldRef> instead of <Group> under <Analysis>''')

        parser.add_argument('-i', '--inputCSV', default=None, required=True,
                            help='''The pathname of the file to import''')

        parser.add_argument('-m', '--modifies', default=DEFAULT_MODIFIES,
                            help=f'''The name to use in the <Field modifies="NAME"> element. 
                            Default is "{DEFAULT_MODIFIES}"''')

        parser.add_argument('-n', '--count', type=int, default=0,
                            help='''The number of rows to import from the CSV file. 
                            Default is 0, which means import all rows.''')

        parser.add_argument('-o', '--outputXML', default=None,
                            help='''The pathname of the XML file to create. Default is the same
                            name as the input CSV file, but with the extension changed to "xml". Refuses
                            to overwrite an existing file unless --overwrite is specified.''')

        parser.add_argument('--overwrite', action='store_true',
                            help='''If set, allows existing XML file to be overwritten.''')

        parser.add_argument('-p', '--fromPackage', action='store_true',
                            help='''If specified, the inputCSV argument is treated as relative to 
                            the opgee package and loaded as an internal resource.''')

        parser.add_argument('-s', '--skipFields', action=ParseCommaList,
                            help='''Comma-delimited list of field names to exclude from analysis''')

        return parser

    def run(self, args, tool):
        from ..error import CommandlineError

        input_csv = args.inputCSV
        if input_csv is None:
            raise CommandlineError('Required input CSV is missing')

        input_path = Path(input_csv)
        from_package = args.fromPackage

        if not input_path.exists() and not from_package:
            raise CommandlineError(f"Input file '{input_path}' does not exist. (Hint: do you need to specify --fromPackage?)")

        output_xml = args.outputXML
        output_path = Path(output_xml) if output_xml else input_path.with_stem('xml')

        if output_path.exists() and not args.overwrite:
            raise CommandlineError(f"Refusing to overwrite '{output_path}'; use --overwrite to override this.")

        import_fields(input_csv, output_xml, args.analysis, count=args.count,
                      modifies=args.modifies, from_package=from_package, skip_fields=args.skipFields, use_group=args.use_group)
