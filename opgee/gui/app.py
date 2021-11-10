#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from collections import defaultdict
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_cytoscape as cyto
from dash.dependencies import Input, Output, State, ClientsideFunction
import dash_table
from pathlib import Path
# import json
# import plotly.graph_objs as go
from textwrap import dedent as d

from .. import Process
from ..attributes import AttrDefs
from ..config import getParam
from ..model import ModelFile
from ..gui.widgets import attr_inputs, gui_switches
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

def field_network_graph(field, show_streams_to_env=False, show_stream_contents=False, show_disabled_procs=False):
    nodes = [{'data': {'id': name, 'label': name},
              'classes': ('enabled' if proc.enabled else 'disabled')} for name, proc in field.process_dict.items()
             if show_disabled_procs or proc.enabled]  # , 'size': 150  didn't work

    edges = [{'data': {'id': name, 'source': s.src_name, 'target': s.dst_name, 'contents': ', '.join(s.contents)}} for
             name, s in field.stream_dict.items() if (
                     (show_streams_to_env or s.dst_name != "Environment") and
                     (show_disabled_procs or (s.dst_proc.enabled and s.src_proc.enabled))
             )]

    edge_color = 'maroon'
    node_color = 'sandybrown'

    layout = cyto.Cytoscape(
        id='network-layout',
        responsive=True,
        elements=nodes + edges,
        autounselectify=False,
        autoungrabify=True,
        userPanningEnabled=True, # False,  # may need to reconsider this when model is bigger
        userZoomingEnabled=True, # False,  # automatic zoom when user changes browser size still works
        style={'width': '100%',
               # 'height': '100%',
               'height': '600px',
               # not sure any of this really works
               'autosize': 'true',
               'resize': 'inherit',
               'overflow': 'auto',
               'display' : 'flex',
               },
        # style={'width': '100%', 'height': '500px', 'resize': 'inherit'},
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
                    'width': '30',
                    'height': '30',
                }
            },
            {
                'selector': '.disabled',
                'style': {
                    'background-color': 'gray',
                }
            },
            {
                'selector': 'edge',
                'style': {
                    'curve-style': 'bezier',
                    # 'mid-target-arrow-color': edge_color,
                    # 'mid-target-arrow-shape': 'triangle',
                    'target-arrow-color': edge_color,
                    'target-arrow-shape': 'triangle',
                    # 'arrow-scale': 1.5,
                    'line-color': edge_color,
                    'line-opacity': 0.50,
                    'width': 1,
                    'target-distance-from-node': 1,  # stop just short of the node
                    'source-distance-from-node': 1,

                    # "width": "mapData(weight, 0, 30, 1, 8)",
                    # "content": "data(weight)",
                    # "overlay-padding": "30px",
                    'label': 'data(contents)',
                    'text-opacity': 0.5 if show_stream_contents else 0.0,
                    'text-rotation': 'autorotate',
                    'text-margin-y': -10,
                    'text-margin-x': 7,
                    'text-background-color': 'blue',
                    "font-size": "14px",
                }
            },
        ]
    )
    node_color = 'sandybrown'


    # noinspection PyCallingNonCallable
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
    totals = df.sum(axis='rows')
    totals.name = 'Total'
    df.append(totals)
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


def processes_layout(app, field, show_streams_to_env=False, show_stream_contents=False, show_disabled_procs=False):
    # the main row
    # noinspection PyCallingNonCallable
    layout = html.Div([

        html.Center(
            html.Div(
                className="row",
                children=[
                    gui_switches(),
                    html.Br(),
                ]
            ),
        ),

        # graph component
        html.Div(
            id='field-network-graph-div',
            className="row",
            children=[
                field_network_graph(field,
                                    show_streams_to_env=show_streams_to_env,
                                    show_stream_contents=show_stream_contents,
                                    show_disabled_procs=show_disabled_procs)
            ],
            style={
                'resize': 'vertical',
                'overflow': 'auto',
                'height' : '35%',

                'autosize': 'true',
                'display': 'flex',
            }
        ),

        html.Div(
            children=[],
            className="row",
            id='emissions-table',
            style={
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


def settings_layout(field):
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


def results_layout(field):
    # noinspection PyCallingNonCallable
    layout = html.Div([
        html.H3('Results'),
        html.Div('', id='ci-text',
                 className="row",
                 # style={'textAlign': "center"},
                 ),
        html.Center(
            dcc.Graph(id="ci-barchart", style={"width": "600px"}),
        ),
    ], className="row",
        style={  # 'display': 'flex',
            'align-items': 'center',
            'textAlign': "center",
            'justify-content': 'center'
        }
    )
    return layout


#
# TBD: Really only works on a current field.
#
def generate_settings_callback(app, analysis, field):
    """
    Generate a callback for all the inputs in the Settings tab by walking the
    attribute definitions dictionary. Each attribute `attr_name` in class
    `class_name` corresponds to an input element with id f"{class_name}:{attr_name}"

    :param app: a Dash app instance
    :param ids: (list(str)) ids of Dropdown controllers to generate callbacks for.
    :return: none
    """
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
            print(f"Class {class_name} has no attributes")

    # First element is the filename field, we pop() this before processing all the generated inputs
    # state_list = [State('settings-filename', 'value')] + [State(id, 'value') for id in ids]
    state_list = [State(id, 'value') for id in ids]

    def func(n_clicks, xml_path, *values):
        if n_clicks == 0 or not values or not xml_path:
            return 'Save attributes to an xml file'
        else:
            save_attributes(xml_path, ids, values, analysis, field)
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


def app_layout(app, model, analysis):
    analysis_names = [analysis.name for analysis in model.analyses()]

    pulldown_style = {
        'width': '200px',
        'textAlign': 'center',
        'vertical-align': 'middle',
        'display': 'inline-block'
    }

    label_style = {
        'font-weight': 'bold'
    }

    horiz_space = html.Span("", style={'width': '50px', 'display': 'inline-block'})

    # noinspection PyCallingNonCallable
    layout = html.Div([
        dcc.Store(id='analysis-and-field', storage_type='session'),

        # TBD: Experiment to see if client-side function fixes graph resizing problem, per
        # https://stackoverflow.com/questions/55462861/dash-dynamic-layout-does-not-propagate-resized-graph-dimensions-until-window-i
        html.Div(id="output-clientside"),

        html.Div([
            html.H1(app.title),

            html.Div([
                html.Center([
                    html.Span("Model: ", style=label_style),
                    html.Span(f"{model.pathname}"),
                    horiz_space,

                    html.Span("Analysis: ", style=label_style),
                    dcc.Dropdown(
                        id='analysis-selector',
                        placeholder='Select analysis...',
                        options=[{'value': name, 'label': name} for name in analysis_names],
                        value=analysis.name,
                        style=pulldown_style,
                    ),
                    horiz_space,

                    html.Span('Field: ', style=label_style),
                    dcc.Dropdown(
                        id='field-selector',
                        placeholder='Select field...',
                        options=[{'value': 'none', 'label': 'none'}],
                        value='none',
                        style=pulldown_style,
                    )
                ]),
                html.Br(),
                html.Button('Run model', id='run-button', n_clicks=0),
                dcc.Markdown(id='run-model-status'),
            ],
            # style = {'height': '130px'}
    ),
        ],
            style={'textAlign': 'center'}
        ),

        html.Div([
            dcc.Tabs(
                id="tabs",
                value='processes',
                parent_className='custom-tabs',
                className='custom-tabs-container',
                children=[
                    dcc.Tab(
                        children=[],  # see processes_layout()
                        label='Processes',
                        value='processes',
                        className='custom-tab',
                        selected_className='custom-tab--selected'
                    ),
                    dcc.Tab(
                        children=[],  # see settings_layout()
                        label='Settings',
                        value='settings',
                        className='custom-tab',
                        selected_className='custom-tab--selected'
                    ),
                    dcc.Tab(
                        children=[],  # see results_layout()
                        label='Results',
                        value='results',
                        className='custom-tab',
                        selected_className='custom-tab--selected'
                    ),
                ]
            ),
            html.Div(id='tab-content')
        ])
    ])
    return layout


def get_analysis_and_field(current_model, data):
    analysis = current_model.get_analysis(data['analysis'])
    field = analysis.get_field(data['field'], raiseError=False) or analysis.first_field()

    return analysis, field


def main(args):
    from ..version import VERSION

    mf = ModelFile(args.modelFile, add_stream_components=args.add_stream_components, use_class_path=args.use_class_path)
    model = mf.model

    analysis_name = args.analysis
    field_name = args.field

    initial_analysis = model.get_analysis(analysis_name)
    # initial_field = model.get_field(field_name)  # deprecated?

    # import the css template, and pass the css template into dash
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
    app.config['suppress_callback_exceptions'] = True
    app.title = "OPGEEv" + VERSION  # OPGEEv4.0a0

    # TBD:
    # - text field (or Open panel) to select a model XML file to run? Or select this from command-line?
    #   - dcc.Upload allows a file to be uploaded. Could be useful in the future.
    # - add dcc.Dropdown from Analyses in a model or to run just one field
    #
    # TBD: use "app.config['suppress_callback_exceptions'] = True" to not need to call tab-layout fns in this layout def

    app.layout = app_layout(app, model, initial_analysis)

    # per https://stackoverflow.com/questions/55462861/dash-dynamic-layout-does-not-propagate-resized-graph-dimensions-until-window-i
    app.clientside_callback(
        ClientsideFunction(namespace="clientside", function_name="resize"),
        Output("output-clientside", "children"),
        [Input("network-layout", "figure")],
    )

    @app.callback(
        Output('field-selector', 'options'),
        Input('analysis-selector', 'value')
    )
    def field_pulldown(analysis_name):
        analysis = model.get_analysis(analysis_name)
        field_names = [field.name for field in analysis.fields()]
        options = [{'label': name, 'value': name} for name in field_names]
        return options

    @app.callback(
        Output('field-selector', 'value'),
        Input('field-selector', 'options'),
    )
    def field_pulldown(options):
        value = options[0]['value']
        return value

    @app.callback(
        Output('analysis-and-field', 'data'),
        Input('field-selector', 'value'),
        Input('analysis-selector', 'value'),
    )
    def switch_fields(field_name, analysis_name):
        analysis = model.get_analysis(analysis_name)
        field = analysis.get_field(field_name, raiseError=False) or analysis.first_field()
        generate_settings_callback(app, analysis, field)
        return dict(analysis=analysis_name, field=field_name)

    @app.callback(
        Output('emissions-and-energy', 'children'),
        Input('network-layout', 'tapNodeData'),
        State('analysis-and-field', 'data'))
    def display_emissions_and_energy(node_data, analysis_and_field):
        if node_data:
            analysis, field = get_analysis_and_field(model, analysis_and_field)

            proc_name = node_data['id']
            proc = field.find_process(proc_name)
            digits = 2

            header = f"Process: {proc_name}\n"

            # display values without all the Series stuff
            rates = proc.get_emission_rates(analysis)
            emissions_str = f"\nEmissions: (tonne/day)\n{rates.astype(float)}"
            # values = '\n'.join([f"{name:4s} {round(value.m, digits)}" for name, value in rates.items()])
            # emissions_str = f"\nEmissions: (tonne/day)\n{values}"

            rates = proc.get_energy_rates(analysis)
            values = '\n'.join([f"{name:19s} {round(value.m, digits)}" for name, value in rates.items()])
            energy_str = f"\n\nEnergy use: (mmbtu/day)\n{values}"

            # display intermediate results
            intermediate_str = ''
            intermediate = proc.get_intermediate_results()
            if intermediate is not None:
                intermediate_str += '\n\n** Intermediate results **'
                for key, (energy, emissions) in intermediate.items():
                    rates = emissions.rates(gwp=analysis.gwp)
                    em_str = f"\nEmissions: (tonne/day)\n{rates.astype(float)}"

                    rates = energy.rates()
                    values = '\n'.join([f"{name:19s} {round(value.m, digits)}" for name, value in rates.items()])
                    en_str = f"\nEnergy use: (mmbtu/day)\n{values}"

                    intermediate_str += f"\n\n{key}:\n{em_str}\n{en_str}"

            return header + emissions_str + energy_str + intermediate_str
        else:
            return ''

    @app.callback(Output('stream-data', 'children'),
                  Input('network-layout', 'tapEdgeData'),
                  State('analysis-and-field', 'data'))
    def display_edge_data(data, analysis_and_field):
        import pandas as pd

        if data:
            analysis, field = get_analysis_and_field(model, analysis_and_field)

            name = data['id']
            stream = field.find_stream(name)
            with pd.option_context('display.max_rows', None,
                                   'precision', 3):
                nonzero = stream.components.query('solid > 0 or liquid > 0 or gas > 0')
                components = str(nonzero.astype(float)) if len(nonzero) else None

            text = f"{name} (tonne/day)\n{components}" if components else f"{name}:\n<empty stream>"
            return html.Pre(text)

    @app.callback(
        Output('run-model-status', 'children'),
        Input('run-button', 'n_clicks'),
        State('analysis-and-field', 'data'))
    def update_output(n_clicks, analysis_and_field):
        if n_clicks:
            analysis, field = get_analysis_and_field(model, analysis_and_field)
            # TBD: get user selections from radio buttons and pass to run method
            # TBD: have run method take optional args for all the run parameters, defaulting to what's in the model file
            field.run(analysis)
            field.report(analysis)
            return "Model has been run"
        else:
            return "Model has not been run"

    @app.callback(
        Output('emissions-table', 'children'),
        Input('tabs', 'value'),
        Input('run-model-status', 'children'),
        Input('analysis-and-field', 'data'))
    def update_result_table(tab, status, analysis_and_field):
        analysis, field = get_analysis_and_field(model, analysis_and_field)

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
                               children=[emissions_table(analysis, container.procs)])
                elt.children.append(div)

        # noinspection PyCallingNonCallable
        item = html.Details(open=True, children=[html.Summary("Process Emissions")])
        add_children(field, item)
        return item

    @app.callback(
        Output('field-network-graph-div', 'children'),
        Input('show-streams-to-env', 'value'),
        Input('show-stream-contents', 'value'),
        Input('show-disabled-procs', 'value'),
        State('analysis-and-field', 'data'),
    )
    def redraw_network_graph(show_streams_to_env, show_stream_contents, show_disabled_procs,
                             analysis_and_field):
        analysis, field = get_analysis_and_field(model, analysis_and_field)
        return field_network_graph(field,
                                   show_streams_to_env=show_streams_to_env,
                                   show_stream_contents=show_stream_contents,
                                   show_disabled_procs=show_disabled_procs)

    @app.callback(
        Output('tab-content', 'children'),
        Input('tabs', 'value'),
        Input('analysis-and-field', 'data'),
    )
    def render_content(tab, analysis_and_field):
        analysis, field = get_analysis_and_field(model, analysis_and_field)

        if tab == 'processes':
            return processes_layout(app, field)

        elif tab == 'settings':
            return settings_layout(field)

        elif tab == 'results':
            return results_layout(field)

    @app.callback(
        Output('ci-text', 'children'),
        Input('run-button', 'n_clicks'),
        Input('analysis-and-field', 'data'))
    def ci_text(n_clicks, analysis_and_field):
        analysis, field = get_analysis_and_field(model, analysis_and_field)

        ci = field.carbon_intensity.m
        fn_unit = analysis.attr('functional_unit')
        en_basis = analysis.attr('energy_basis')
        return f"CI: {ci:0.2f} g CO2e/MJ {en_basis} of {fn_unit}"

    @app.callback(
        Output('ci-barchart', 'figure'),
        Input('run-button', 'n_clicks'),
        Input('analysis-and-field', 'data'))
    def ci_barchart(n_clicks, analysis_and_field):
        # import plotly.express as px
        import pandas as pd
        import plotly.graph_objs as go

        analysis, field = get_analysis_and_field(model, analysis_and_field)

        fn_unit = analysis.attr('functional_unit')

        value_col = r'$g CO_2 MJ^{-1}$'
        df = pd.DataFrame({"category": ["Exploration", "Surface Processing", "Transportation"],
                           "value": [1.5, 2.2, 3.1],
                           "name": [fn_unit] * 3})

        # TBD: looks too inflexible. Probably use a lower-level bar chart go.bar?
        # import plotly.graph_objects as go
        fn_unit_list = [fn_unit] * 3

        # fig = go.Figure(data=[
        #     go.Bar(name='SF Zoo', x=fn_unit_list, y=[20, 14, 23]),
        #     go.Bar(name='LA Zoo', x=fn_unit_list, y=[12, 18, 29])
        # ])

        fig = go.Figure(data=[go.Bar(name=row.category, x=[row.name], y=[row.value]) for idx, row in df.iterrows()])
        # Change the bar mode
        fig.update_layout(barmode='stack',
                          yaxis_title="g CO2 per MJ",  # doesn't render in latex: r'g CO$_2$ MJ$^{-1}$',
                          xaxis_title=f'Carbon Intensity of {fn_unit.title()}')

        # fig = px.bar(df, x="Name", y=value_col, color="Category", barmode="stack",
        #              hover_data=[value_col],
        #              )
        return fig

    app.run_server(debug=True)
