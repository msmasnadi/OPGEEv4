#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from collections import defaultdict
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_cytoscape as cyto
from dash.dependencies import Input, Output, State
import dash_table
from pathlib import Path
#import json
#import plotly.graph_objs as go
from textwrap import dedent as d

from .. import Process
from ..attributes import AttrDefs
from ..config import getParam
from ..model import ModelFile
from ..gui.widgets import attr_inputs
from ..log import getLogger
from ..utils import mkdirs

_logger = getLogger(__name__)

# Required to load separator_model.xml
class After(Process):
    def run(self, analysis):
        pass

    def impute(self):
        pass

# Load extra layouts
# cyto.load_extra_layouts()   # required for cose-bilkent

def field_network_graph(field):

    nodes = [{'data': {'id': name, 'label':name}} for name in field.process_dict.keys()]
    edges = [{'data': {'id': name, 'source': s.src_name, 'target': s.dst_name}} for name, s in field.stream_dict.items()]

    edge_color = 'maroon'
    node_color = 'sandybrown'

    # noinspection PyCallingNonCallable
    layout = html.Div([
        cyto.Cytoscape(
            id='network-layout',
            responsive=True,
            elements=nodes+edges,
            autounselectify=False,
            autoungrabify=True,
            userPanningEnabled=False,   # may need to reconsider this when model is bigger
            userZoomingEnabled=False,   # automatic zoom when user changes browser size still works
            style={'width': '100%', 'height': '450px'},
            layout={
                'name': 'breadthfirst',
                'roots': '[id = "Reservoir"]'
            },
            stylesheet=[
                {
                    'selector': 'node',
                    'style': {
                        'label': 'data(id)',
                        'background-color': node_color,
                    }
                },
                {
                    'selector': 'edge',
                    'style': {
                        'curve-style': 'bezier',
                        'mid-target-arrow-color': edge_color,
                        'mid-target-arrow-shape': 'triangle',
                        'arrow-scale': 1.5,
                        'line-color': edge_color,
                    }
                },
            ]
        )
    ])
    return layout

# styles: for right side hover/click component
styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}

def emissions_table(analysis, procs):
    import pandas as pd
    from ..emissions import Emissions

    columns = [{'name': 'Name', 'id': 'Name'}] + [{'name': col, 'id': col} for col in Emissions.categories]

    def series_for_df(proc):
        rates = proc.get_emission_rates(analysis).astype(float)
        s = rates.T.GHG
        s.name = proc.name
        return s

    df = pd.DataFrame(data=[series_for_df(proc) for proc in procs])
    df.loc['Total', :] = df.sum(axis='rows')
    df.reset_index(inplace=True)
    df.rename({'index': 'Name'}, axis='columns', inplace=True)

    # convert to scientific notation
    for col_name, col in df.iteritems():
        if col.dtype == float:
            df[col_name] = col.apply(lambda x: '{:.2E}'.format(x))

    data = df.to_dict('records')  # TBD: use scientific notation?

    text_cols = ['Name']

    tbl = dash_table.DataTable(
        columns=columns,
        data=data,
        style_as_list_view=True,
        style_cell={'padding': '5px'},
        style_header={
            'backgroundColor': 'white',
            'fontWeight': 'bold'
        },
        style_cell_conditional=[
            {
                'if': {
                    'column_id': c
                },
                'textAlign': 'left',
                'font-family': 'sans-serif',
            } for c in text_cols
        ],
        style_data_conditional=[
            {
                'if': {
                    'filter_query': '{Name} = "Total"',
                },
                'fontWeight': 'bold'
            },
        ]
    )
    return tbl

# def overview_layout(app):
#     layout = html.Div([
#         # Title
#         html.Div(
#             [],
#             className="row",
#             style={'textAlign': "center"}
#         ),
#     ])
#     return layout

def processes_layout(app, current_field):
    # the main row
    # noinspection PyCallingNonCallable
    layout = html.Div([
            # html.H3('Processes', style={'textAlign': "center"}),

            # graph component
            html.Div(
                # className="twelve columns",
                className="row",
                children=[
                    # dcc.Graph(id="my-graph", figure=field_network_graph(current_field))
                    field_network_graph(current_field)
                ],
            ),

            html.Div(
                children=[],
                className="row",
                id='emissions-table',
                style = {
                    'background-color': 'aliceblue',
                    'border-radius': '4px',
                    'border': '1px solid',
                }
            ),

            html.Br(),

            # output components
            html.Div(
                className="twelve columns",
                children=[
                    html.Div(
                        className='six columns',
                        children=[
                            dcc.Markdown(d("""
                            **Emissions and energy use**
                            """), style={'margin-left': '4px'}),
                            html.Pre(id='emissions-and-energy',
                                     style={'margin-left': '8px'})
                        ],
                        style={
                            # 'height': '400px',
                            'display': 'inline-block',
                            'background-color': 'aliceblue',
                            'border-radius': '4px',
                            'border': '1px solid',
                        }),

                    html.Div(
                        className='six columns',
                        children=[
                            dcc.Markdown(d("""
                            **Stream Data**
                            """), style={'margin-left': '8px'}),
                            html.Div(
                                children=[],
                                id='stream-data',
                                style={'margin-left': '8px'},
                            )
                        ],
                        style={
                            # 'height': '400px',
                            'display': 'inline-block',
                            'background-color': 'aliceblue',
                            'border-radius': '4px',
                            'border': '1px solid',
                        })
                ],
                style={'height': '400px', 'display': 'inline-block'})
        ],
        className="row",
    )
    return layout

def settings_layout(current_field):
    proc_names = sorted([proc.name for proc in current_field.processes()])
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

#
# TBD: Really only works on a current field.
#
def generate_settings_callback(app, current_analysis, current_field):
    """
    Generate a callback for all the inputs in the Settings tab by walking the
    attribute definitions dictionary. Each attribute `attr_name` in class
    `class_name` corresponds to an input element with id f"{class_name}:{attr_name}"

    :param app: a Dash app instance
    :param ids: (list(str)) ids of Dropdown controllers to generate callbacks for.
    :return: none
    """
    from lxml import etree as ET

    class_names = ['Model', 'Analysis', 'Field'] + [proc.name for proc in current_field.processes()]

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
            print(f"Class {class_name} has no attributes")

    # First element is the filename field, we pop() this before processing all the generated inputs
    # state_list = [State('settings-filename', 'value')] + [State(id, 'value') for id in ids]
    state_list = [State(id, 'value') for id in ids]

    def func(n_clicks, xml_path, *values):
        if n_clicks == 0 or not values or not xml_path:
            return 'Save attributes to an xml file'
        else:
            save_attributes(xml_path, ids, values, current_analysis, current_field)
            return f"Attributes saved to '{xml_path}'"

    app.callback(Output('save-button-status', 'children'),
                 Input('save-settings-button', 'n_clicks'),
                 Input('settings-filename', 'value'),
                 state=state_list)(func)

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

def app_layout(app):
    # noinspection PyCallingNonCallable
    layout = html.Div([
        html.Div([
            html.H1(app.title),

            html.Div([
                html.Button('Run model', id='run-button', n_clicks=0),
                dcc.Markdown(id='run-model-status')
            ],
                style={'height': '100px'}
            ),
        ],
            style={'textAlign': "center"}
        ),

        html.Div([
            dcc.Tabs(
                id="tabs-with-classes",
                value='processes',
                parent_className='custom-tabs',
                className='custom-tabs-container',
                children=[
                    # dcc.Tab(
                    #     children=[],        # overview_layout(app)
                    #     label='Overview',
                    #     value='overview',
                    #     className='custom-tab',
                    #     selected_className='custom-tab--selected'
                    # ),
                    dcc.Tab(
                        children=[],  # processes_layout(app, current_field)
                        label='Processes',
                        value='processes',
                        className='custom-tab',
                        selected_className='custom-tab--selected'
                    ),
                    dcc.Tab(
                        children=[],  # settings_layout(app)
                        label='Settings',
                        value='settings',
                        className='custom-tab',
                        selected_className='custom-tab--selected'
                    ),
                ]
            ),
            html.Div(id='tabs-content-classes')
        ])
    ])
    return layout

def main(args):
    from ..version import VERSION

    mf = ModelFile(args.modelFile, add_stream_components=args.add_stream_components, use_class_path=args.use_class_path)
    current_model = mf.model

    field_name = args.field
    field = current_model.get_field(field_name)

    analysis_name = args.analysis
    current_analysis = current_model.get_analysis(analysis_name)
    current_field = field

    # import the css template, and pass the css template into dash
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
    app.config['suppress_callback_exceptions'] = True
    app.title = "OPGEEv" + VERSION # OPGEEv4.0a0

    # TBD:
    # - text field (or Open panel) to select a model XML file to run? Or select this from command-line?
    #   - dcc.Upload allows a file to be uploaded. Could be useful in the future.
    # - add dcc.Dropdown from Analyses in a model or to run just one field
    #
    # Note: dcc.Store provides a browser-side caching mechanism

    # TBD: use "app.config['suppress_callback_exceptions'] = True" to not need to call tab-layout fns in this layout def

    app.layout = app_layout(app)

    # callback for right side components
    @app.callback(
        Output('emissions-and-energy', 'children'),
        [Input('network-layout', 'tapNodeData')])
    def display_emissions_and_energy(node_data):
        if node_data:
            proc_name = node_data['id']
            proc = current_field.find_process(proc_name)
            digits = 2

            header = f"Process: {proc_name}\n"

            # display values without all the Series stuff
            rates = proc.get_emission_rates(current_analysis)
            emissions_str = f"\nEmissions: (tonne/day)\n{rates.astype(float)}"
            # values = '\n'.join([f"{name:4s} {round(value.m, digits)}" for name, value in rates.items()])
            # emissions_str = f"\nEmissions: (tonne/day)\n{values}"

            rates = proc.get_energy_rates(current_analysis)
            values = '\n'.join([f"{name:19s} {round(value.m, digits)}" for name, value in rates.items()])
            energy_str = f"\n\nEnergy use: (mmbtu/day)\n{values}"

            return header + emissions_str + energy_str
        else:
            return ''

    @app.callback(Output('stream-data', 'children'),
                  [Input('network-layout', 'tapEdgeData')])
    def display_edge_data(data):
        import pandas as pd

        if data:
            name = data['id']
            stream = current_field.find_stream(name)
            with pd.option_context('display.max_rows', None,
                                   'precision', 3):
                    nonzero = stream.components.query('solid > 0 or liquid > 0 or gas > 0')
                    components = str(nonzero.astype(float)) if len(nonzero) else None

            text = f"{name} (tonne/day)\n{components}" if components else f"{name}:\n<empty stream>"
            return html.Pre(text)

    @app.callback(
        Output('run-model-status', 'children'),
        [Input('run-button', 'n_clicks')])
    def update_output(n_clicks):
        if n_clicks:
            # TBD: get user selections from radio buttons and pass to run method
            # TBD: have run method take optional args for all the run parameters, defaulting to what's in the model file
            current_field.run(current_analysis)
            current_field.report(current_analysis)
            return "Model has been run"
        else:
            return "Model has not been run"

    @app.callback(
        Output('emissions-table', 'children'),
        [Input('tabs-with-classes', 'value'),
         Input('run-model-status', 'children')])
    def update_result_table(tab, status):
        # if tab != 'processes':
        #     return ""

        style = {'margin-left': '16px'}

        # recursively create expanding aggregator structure with emissions (table, eventually)
        def add_children(container, elt):
            for agg in container.aggs:
                # noinspection PyCallingNonCallable
                details = html.Details(children=[html.Summary(html.B(agg.name))], style=style)
                elt.children.append(details)
                add_children(agg, details)

            if container.procs:
                # noinspection PyCallingNonCallable
                div = html.Div(style=style,
                               children=[emissions_table(current_analysis, container.procs)])
                elt.children.append(div)

        # noinspection PyCallingNonCallable
        elt = html.Details(open=True, children=[html.Summary("Process Emissions")])
        add_children(current_field, elt)
        return elt

    @app.callback(
        Output('tabs-content-classes', 'children'),
        Input('tabs-with-classes', 'value'))
    def render_content(tab):
        if tab == 'processes':
            return processes_layout(app, current_field)

        elif tab == 'settings':
            return settings_layout(current_field)

        # elif tab == 'overview':
        #     return overview_layout(app)

    generate_settings_callback(app, current_analysis, current_field)

    app.run_server(debug=True)

