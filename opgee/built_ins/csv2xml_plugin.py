"""
.. Import edited_fields.csv (derived from OPGEEv3 workbook's "Input" sheet) to XML

.. codeauthor:: <rich@plevin.com>

.. Copyright (c) 2021  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from pathlib import Path
from ..subcommand import SubcommandABC, clean_help
from ..log import getLogger

_logger = getLogger(__name__)

def read_fields(csv_path, from_package=False):
    import pandas as pd
    from ..pkg_utils import resourceStream

    stream = resourceStream(csv_path) if from_package else csv_path
    df = pd.read_csv(stream, index_col=0)

    dtypes = df['Type']
    df.drop('Type', axis='columns', inplace=True)

    dft = df.transpose()
    return (dft, dtypes)

    # metadata = df[['Description', 'Unit']].copy()
    # metadata.Unit.fillna('', inplace=True)
    # df.drop(['Category', 'Description', 'Unit'], axis='columns', inplace=True)
    # dft = df.transpose()
    # return (metadata, dft)

def import_fields(csv_path, xml_path, analysis_name, count=0, from_package=False):
    """
    Import Field information from a CSV file.

    :param csv_path: (str or Path) the CSV file to read
    :param xml_path: (str or Path) the XML file to create
    :param count: (int) if count > 0, import only the first `count` fields
    :param from_package: (bool) if True, treat `streams_csv_path` as relative to the
       opgee package and load the file from the internal package resource.
    :return:
    """
    from lxml import etree as ET
    import numpy as np

    fields, dtypes = read_fields(csv_path, from_package=from_package)

    known_types = {'int' : int, 'float' : float, 'str' : str}

    if count:
        fields = fields.loc[fields.index[:count]]

    root = ET.Element('Model')

    if not analysis_name:
        p = Path(csv_path)
        analysis_name = p.name[:-(len(p.suffix))]

    analysis = ET.SubElement(root, 'Analysis', attrib={'name' : analysis_name})

    # Convert fields to xml
    for field_name, row in fields.iterrows():
        field = ET.SubElement(analysis, 'Field',
                              attrib={'name' : field_name, 'modifies' : 'US_FW'})

        for attr, value in row.items():

            # don't include unspecified attributes
            try:
                if np.isnan(value):
                    continue
            except:
                pass  # np.isnan() fails for non-numeric types; ignore it

            if value == '' or value is None:
                continue

            attrib = dict(name=attr)
            a = ET.SubElement(field, 'A', attrib=attrib)
            dtype = dtypes[attr]
            type_fn = known_types[dtype]
            try:
                a.text = str(type_fn(value))
            except Exception as e:
                print(e)

    _logger.info('Writing %s', xml_path)

    tree = ET.ElementTree(root)
    tree.write(xml_path, xml_declaration=True, pretty_print=True, encoding='utf-8')

class XmlCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Convert various CSV files to their corresponding XML representation.'''}
        super().__init__('csv2xml', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        parser.add_argument('-a', '--analysis',
                            help='''The name to give the <Analysis> element. Default is the file basename 
                            with the extension removed.''')
        parser.add_argument('-n', '--count', type=int, default=0,
                            help=clean_help('''The number of rows to import from the CSV file. 
                            Default is 0, which means import all rows.'''))

        parser.add_argument('-p', '--fromPackage', action='store_true',
                            help=clean_help('''If specified, the inputCSV argument is treated as relative to 
                            the opgee package and loaded as an internal resource.'''))

        parser.add_argument('-i', '--inputCSV', default=None, required=True,
                            help=clean_help('''The pathname of the file to import'''))

        parser.add_argument('-o', '--outputXML', default=None,
                            help=clean_help('''The pathname of the XML file to create. Default is the same
                            name as the input CSV file, but with the extension changed to "xml". Refuses
                            to overwrite an existing file unless --overwrite is specified.'''))

        parser.add_argument('--overwrite', action='store_true',
                            help=clean_help('''If set, allows existing XML file to be overwritten.'''))

        format_default = 'fields'
        format_choices = [format_default, 'attributes'] # extend as needed
        parser.add_argument('-f', '--format', choices=format_choices, default=format_default,
                            help=clean_help(f'''Which type of conversion to perform. Default is "{format_default}".'''))

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

        import_fields(input_csv, output_xml, args.analysis, count=args.count, from_package=from_package)
