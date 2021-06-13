#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import json
import networkx as nx
import pydot
import plotly.graph_objs as go
from textwrap import dedent as d

from .. import Process
from ..model import ModelFile
from ..gui.widgets import radio_items
from ..log import getLogger

_logger = getLogger(__name__)

# Required to load separator_model.xml
class After(Process):
    def run(self, analysis):
        pass

    def impute(self):
        pass

def field_network_graph(field):
    graph = pydot.Dot('model', graph_type='digraph', bgcolor='white')

    for name, proc in field.process_dict.items():
        graph.add_node(pydot.Node(name))

    for name, stream in field.stream_dict.items():
        graph.add_edge(pydot.Edge(stream.src_name, stream.dst_name))

    # TBD: just use networkx without pydot
    # convert graph to networkx
    G = nx.nx_pydot.from_pydot(graph)

    #pos = nx.drawing.layout.spring_layout(G)
    pos = nx.fruchterman_reingold_layout(G)
    for node in G.nodes:
        G.nodes[node]['pos'] = list(pos[node])

    # generate as many colors in a range as there are edges
    # colors = list(Color('lightcoral').range_to(Color('darkred'), len(G.edges())))
    # colors = ['rgb' + str(x.rgb) for x in colors]

    traces = []  # contains edge_trace and node_trace

    # TBD: might be useful to be able to click on a Stream (edge) to display it
    # No need to draw these since we draw the arrows as annotations
    # for edge, color in zip(G.edges, colors):
    #     x0, y0 = G.nodes[edge[0]]['pos']
    #     x1, y1 = G.nodes[edge[1]]['pos']
    #     trace = go.Scatter(x=tuple([x0, x1, None]), y=tuple([y0, y1, None]),
    #                        mode='lines',
    #                        line={'width': 2},
    #                        marker=dict(color=colors),
    #                        line_shape='spline',
    #                        opacity=1)
    #     traces.append(trace)

    mode = 'markers+text'
    node_trace = go.Scatter(x=[], y=[], hovertext=[], text=[], mode=mode, textposition="bottom center",
                            hoverinfo="text", marker={'size': 40, 'color': 'sandybrown'})

    for node in G.nodes():
        x, y = G.nodes[node]['pos']
        proc = field.find_process(node)
        hovertext = f"Consumes: {proc.consumption}<br>Produces: {proc.production}"

        node_trace['x'] += tuple([x])
        node_trace['y'] += tuple([y])
        node_trace['text'] += tuple([proc.name])
        node_trace['hovertext'] += tuple([hovertext])

    traces.append(node_trace)

    layout = go.Layout(title=f"Field: '{field.name}'", showlegend=False,
                       margin={'b': 40, 'l': 40, 'r': 40, 't': 40},
                       xaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False},
                       yaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False},
                       height=600
                       )
    fig = go.Figure(data=traces, layout=layout)

    # Add arrows as annotations
    for edge in G.edges:
        src = edge[0]
        dst = edge[1]
        x0, y0 = G.nodes[src]['pos']
        x1, y1 = G.nodes[dst]['pos']
        fig.add_annotation(
            x=x1,   # arrows' head
            y=y1,   # arrows' head
            ax=x0,  # arrows' tail
            ay=y0,  # arrows' tail
            xref='x', yref='y',
            axref='x', ayref='y',
            text='',  # if you want only the arrow
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor=('black' if src == 'Reservoir' else ('lightslategray' if dst == 'Environment' else 'maroon'))
        )

    return fig

######################################################################################################################################################################
# styles: for right side hover/click component
styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}


# go.Table(header=dict(values=['A Scores', 'B Scores']),
#          cells=dict(values=[[100, 90, 80, 90], [95, 85, 75, 95]])
#
# fig = go.Figure(data=[go.Table(
#     header=dict(values=['A Scores', 'B Scores'],
#                 line_color='darkslategray',
#                 fill_color='lightskyblue',
#                 align='left'),
#     cells=dict(values=[[100, 90, 80, 90], # 1st column
#                        [95, 85, 75, 95]], # 2nd column
#                line_color='darkslategray',
#                fill_color='lightcyan',
#                align='left'))
# ])
def emissions_table(obj):
    rates = obj.emissions.rates()

    tbl = dash_table.DataTable(columns=[{'name': col, 'id': col} for col in rates.index],
                               data=[{col: value.m for col, value in rates.items()}])
    return tbl


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
    app.title = "OPGEEv" + VERSION # OPGEEv4.0a0

    # TBD:
    # - text field (or Open panel) to select a model XML file to run? Or select this from command-line?
    #   - dcc.Upload allows a file to be uploaded. Could be useful in the future.
    # - add dcc.Dropdown from Analyses in a model or to run just one field
    #
    # Note: dcc.Store provides a browser-side caching mechanism


    app.layout = html.Div([
        # Title
        html.Div([html.H1(app.title)],
                 className="row",
                 style={'textAlign': "center"}),

        html.Div(
            className="row",

            # TBD: get all the radio button values from model attributes
            # TBD: to do this, just add the radio button with an id, and populate it in a callback
            # TBD: as in https://dash.plotly.com/basic-callbacks
            # radio buttons
            children=[
                html.Div(
                    className="two columns",
                    children=[
                        radio_items('Energy basis', {'Lower heating value': 'LHV',
                                                     'Higher heating value': 'HHV'
                                                     }, 'LHV'),
                    ],
                ),
                html.Div(
                    className="two columns",
                    children=[
                        radio_items('Functional unit', {'1 MJ Crude oil': 'oil',
                                                        '1 MJ Natural gas': 'gas'
                                                        }, 'oil'),
                    ],
                ),
                html.Div(
                        className="two columns",
                        children=[
                            radio_items('System boundary', {'Field': 'field',
                                                            'Post-transport': 'post-transport',
                                                            'Post-distribution': 'post-distribution',
                                                            }, 'field'),
                        ],
                ),
                html.Div(
                        className="two columns",
                        children=[
                            radio_items('Allocation method', {'Energy basis': 'energy',
                                                              'Displacement': 'displacement'
                                                              }, 'energy'),
                        ],
                ),
                html.Div(
                    className='two columns',
                    children=[
                        html.Button('Run model', id='run-button', n_clicks=0),
                        dcc.Markdown(id='model-status')
                    ],
                    style={'height': '100px'}),
            ],
        ),

        # the main row
        html.Div(
            className="row",
            children=[
                # middle graph component
                html.Div(
                    className="eight columns",
                    children=[
                        dcc.Graph(id="my-graph", figure=field_network_graph(current_field))],
                ),

                # right side two output component
                html.Div(
                    className="four columns",
                    children=[
                        html.Div(
                            className='twelve columns',
                            children=[
                                dcc.Markdown(d("""
                                **Hover Data**
    
                                Emissions and energy use
                                """)),
                                html.Pre(id='hover-data', style=styles['pre'])
                            ],
                            style={'height': '300px'}),

                        html.Div(
                            className='twelve columns',
                            children=[
                                dcc.Markdown(d("""
                                **Click Data**
    
                                Click on points in the graph.
                                """)),
                                html.Pre(id='click-data', style=styles['pre'])
                            ],
                            style={'height': '300px'})
                    ]
                )
            ]
        ),

        html.Div(
            className="row",
            id='emissions-table',
            children = []
        )
    ])

    # callback for left side components
    @app.callback(
        dash.dependencies.Output('my-graph', 'figure'),

        # TBD: this isn't needed, but something was required syntactically... fix it!
        [dash.dependencies.Input('run-button', 'n_clicks')])
    def update_output(n_clicks):
        return field_network_graph(current_field)

    # callback for right side components
    @app.callback(
        dash.dependencies.Output('hover-data', 'children'),
        [dash.dependencies.Input('my-graph', 'hoverData')])
    def display_hover_data(hoverData):
        if hoverData:
            proc_name = hoverData['points'][0]['text']
            proc = current_field.find_process(proc_name)
            digits = 2

            header = f"Process: {proc_name}\n"

            # display values without all the Series stuff
            rates = proc.get_emission_rates(current_analysis)
            values = '\n'.join([f"{name:4s} {round(value.m, digits)}" for name, value in rates.items()])
            emissions_str = f"\nEmissions: (tonne/day)\n{values}"

            rates = proc.get_energy_rates(current_analysis)
            values = '\n'.join([f"{name:19s} {round(value.m, digits)}" for name, value in rates.items()])
            energy_str = f"\n\nEnergy use: (mmbtu/day)\n{values}"

            return header + emissions_str + energy_str
        else:
            return ''

    @app.callback(
        dash.dependencies.Output('click-data', 'children'),
        [dash.dependencies.Input('my-graph', 'clickData')])
    def display_click_data(clickData):
        return json.dumps(clickData, indent=2)

    @app.callback(
        dash.dependencies.Output('model-status', 'children'),
        [dash.dependencies.Input('run-button', 'n_clicks')])
    def update_output(n_clicks):
        if n_clicks:
            # TBD: get user selections from radio buttons and pass to run method
            # TBD: have run method take optional args for all the run parameters, defaulting to what's in the model file
            current_field.run(current_analysis)
            return "Model has been run"
        else:
            return f"Model has not been run"

    @app.callback(
        dash.dependencies.Output('emissions-table', 'children'),
        [dash.dependencies.Input('run-button', 'n_clicks')])
    def update_result_table(n_clicks):
        style = {'margin-left': '16px'}

        # recursively create expanding aggregator structure with emissions (table, eventually)
        def add_children(container, elt):
            for agg in container.aggs:
                details = html.Details(children=[html.Summary(html.B(agg.name))], style=style)
                elt.children.append(details)
                add_children(agg, details)

            for proc in container.procs:
                div = html.Div(style=style,
                               children=[html.I(proc.name), emissions_table(proc)])
                elt.children.append(div)

        elt = html.Details(open=True, children=[html.Summary("Process Emissions")])
        add_children(current_field, elt)
        return elt


    app.run_server(debug=True)

