from collections import defaultdict
from dash import dcc, html
from dash.dependencies import Input, Output, State
from pathlib import Path

from ..attributes import AttrDefs
from ..config import getParam
from ..gui.widgets import attr_inputs
from ..log import getLogger
from ..utils import mkdirs

from .widgets import OpgeePane

_logger = getLogger(__name__)


class SettingsPane(OpgeePane):

    def get_layout(self, field, **kwargs):
        proc_names = sorted([proc.name for proc in field.processes()])
        proc_sections = [attr_inputs(proc_name) for proc_name in proc_names]

        sections = [
                       attr_inputs('Model'),
                       attr_inputs('Analysis'),
                       attr_inputs('Field'),
                   ] + proc_sections

        attributes_xml = getParam('OPGEE.UserAttributesFile') or ''

        # noinspection PyCallingNonCallable
        layout = html.Div([
            html.H3('Settings'),
            html.Div([
                dcc.Input(id='settings-filename', type='text', debounce=True, pattern=r'^.*\.xml$',
                          value=attributes_xml, style={'width': '400px'}),
                html.Button('Save', id='save-settings-button', n_clicks=0),
                dcc.Markdown(id='save-button-status')
            ],
                style={'height': '100px'}),
            html.Div(sections,
                     className="row",
                     ),
        ], style={'textAlign': "center"},
            className="row"
        )
        return layout


    def add_callbacks(self):
        pass


    #
    # TBD: Really only works on a current field.
    #
    def generate_settings_callback(self, analysis, field):
        """
        Generate a callback for all the inputs in the Settings tab by walking the
        attribute definitions dictionary. Each attribute `attr_name` in class
        `class_name` corresponds to an input element with id f"{class_name}:{attr_name}"

        :param analysis: (Analysis)
        ;param field: (Field)
        :return: none
        """
        app = self.app

        class_names = ['Model', 'Analysis', 'Field'] + [proc.name for proc in field.processes()]

        attr_defs = AttrDefs.get_instance()
        class_dict = attr_defs.classes

        ids = []
        for class_name in class_names:
            class_attrs = class_dict.get(class_name)
            if class_attrs:
                for attr_name in class_attrs.attr_dict.keys():
                    id = f"{class_name}:{attr_name}"
                    # print(f"Callback state for input '{id}'")
                    ids.append(id)
            else:
                _logger.debug(f"Class {class_name} has no attributes")

        # First element is the filename field, we pop() this before processing all the generated inputs
        # state_list = [State('settings-filename', 'value')] + [State(id, 'value') for id in ids]
        state_list = [State(id, 'value') for id in ids]

        def func(n_clicks, xml_path, *values):
            if n_clicks == 0 or not values or not xml_path:
                return 'Save attributes to an xml file'
            else:
                self.save_attributes(xml_path, ids, values, analysis, field)
                return f"Attributes saved to '{xml_path}'"

        app.callback(Output('save-button-status', 'children'),
                     Input('save-settings-button', 'n_clicks'),
                     Input('settings-filename', 'value'),
                     *state_list)(func)

    @staticmethod
    def save_attributes(xml_path, ids, values, analysis, field):
        """
        Save changed attributes to the file given by `xml_path`.

        :param xml_path: (str) the pathname of the XML file to write
        :param ids: (list of str) the ids of the attributes associated with `values`. These
            are formed as a colon-separated pair of strings, "class_name:attr_name".
        :param values: (list) the values for the attributes
        :param analysis: (opgee.Analysis) the current Analysis
        :param field: (opgee.Field) the current Field
        :return: none
        """
        from lxml import etree as ET
        from ..core import magnitude
        from ..utils import coercible

        attr_defs = AttrDefs.get_instance()
        class_dict = attr_defs.classes

        class_value_dict = defaultdict(list)

        for id, value in zip(ids, values):
            class_name, attr_name = id.split(':')

            # Don't write out values that are equal to defaults
            class_attrs = class_dict.get(class_name)
            if class_attrs:
                attr_def = class_attrs.attr_dict[attr_name]
                if magnitude(attr_def.default) == coercible(value, attr_def.pytype):
                    continue

            class_value_dict[class_name].append((attr_name, value))

        root = ET.Element('Model')

        for class_name, value_pairs in class_value_dict.items():
            if class_name == 'Model':
                class_elt = root  # Model attributes are top level

            elif class_name == 'Process':
                class_elt = ET.SubElement(root, class_name)

            elif class_name in ('Field', 'Analysis'):
                name = field.name if class_name == 'Field' else analysis.name
                class_elt = ET.SubElement(root, class_name, attrib={'name': name})

            else:  # Process subclass
                class_elt = ET.SubElement(root, 'Process', attrib={'name': class_name})

            for attr_name, value in value_pairs:
                elt = ET.SubElement(class_elt, 'A', attrib={'name': attr_name})
                elt.text = str(value)

        # ET.dump(root)

        # ensure the directory exists
        path = Path(xml_path)
        mkdirs(path.parent)

        _logger.info('Writing %s', xml_path)

        tree = ET.ElementTree(root)
        tree.write(xml_path, xml_declaration=True, pretty_print=True, encoding='utf-8')
