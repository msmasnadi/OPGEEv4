#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_cytoscape as cyto
from dash.dependencies import Input, Output
import dash_table
#import json
#import networkx as nx
#import pydot
#import plotly.graph_objs as go
from textwrap import dedent as d

from .. import Process
from ..model import ModelFile
from ..gui.widgets import attr_options
from ..log import getLogger

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

    layout = html.Div([
        cyto.Cytoscape(
            id='network-layout',
            responsive=True,
            elements=nodes+edges,
            # autolock=True,        # causes drawing weirdness
            autounselectify=False,
            autoungrabify=True,
            userPanningEnabled=False,
            userZoomingEnabled=False,
            # minZoom=0.5,
            # maxZoom=1.5,
            style={'width': '100%', 'height': '450px'},
            layout={
                'name': 'breadthfirst',
                'roots': '[id = "Reservoir"]'

                # 'name': 'cose'
                # 'name': 'grid'
                # 'name': 'circle'
                # 'name': 'concentric'
                # 'name': 'cose-bilkent'
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

######################################################################################################################################################################
# styles: for right side hover/click component
styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}

def emissions_table(analysis, procs):
    import pandas as pd
    from pint import Quantity
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

    def get_magnitude(quantity):
        return quantity.m if isinstance(quantity, Quantity) else quantity

    tbl = dash_table.DataTable(
        columns=columns,
        # data=df.applymap(get_magnitude).to_dict('records'),  # TBD: Force scientific notation
        data=df.round(3).to_dict('records'),  # TBD: Force scientific notation
        # data=df.astype(float).to_dict('records'),
        style_as_list_view=True,
        style_cell={'padding': '5px'},
        style_header={
            'backgroundColor': 'white',
            'fontWeight': 'bold'
        },
        style_cell_conditional=[
            {
                'if': {'column_id': c},
                'textAlign': 'left'
            } for c in ['Name']
        ],
        style_data_conditional=[
            {
                'if': {
                    'filter_query': '{Name} = "Total"',
                    # 'column_id': 'Name'
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
                            """)),
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
                            """)),
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

def settings_layout(app, current_field):

    proc_sections = [attr_options(proc.__class__.__name__) for proc in current_field.processes()]

    sections = [
        # attr_options('Model'),
        attr_options('Analysis'),
        attr_options('Field'),
    ] + proc_sections


    layout = html.Div([
        html.H3('Settings'),
        html.Div(sections,
            className="row",
        ),
    ], style={'textAlign': "center"},
       className="row"
    )
    return layout

def app_layout(app):
    layout = html.Div([
        html.Div([
            html.H1(app.title),

            # html.Br(),

            html.Div([
                html.Button('Run model', id='run-button', n_clicks=0),
                dcc.Markdown(id='model-status')
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
                    components = str(stream.components.astype(float))
            text = f"{name} (tonne/day)\n{components}"
            return html.Pre(text)

    @app.callback(
        Output('model-status', 'children'),
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
         Input('model-status', 'children')])
    def update_result_table(tab, status):
        # if tab != 'processes':
        #     return ""

        style = {'margin-left': '16px'}

        # recursively create expanding aggregator structure with emissions (table, eventually)
        def add_children(container, elt):
            for agg in container.aggs:
                details = html.Details(children=[html.Summary(html.B(agg.name))], style=style)
                elt.children.append(details)
                add_children(agg, details)

            if container.procs:
                div = html.Div(style=style,
                               children=[emissions_table(current_analysis, container.procs)])
                elt.children.append(div)

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
            return settings_layout(app,current_field)

        # elif tab == 'overview':
        #     return overview_layout(app)


    app.run_server(debug=True)

