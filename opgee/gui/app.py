#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import json
import networkx as nx
import pydot
import plotly.graph_objs as go
from textwrap import dedent as d

from opgee import Process
from opgee.model import ModelFile

# import the css template, and pass the css template into dash
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "OPGEE Field Network"

MODEL_XML = '/Users/rjp/repos/OPGEEv4/tests/files/test_separator.xml'
FIELD_NAME = 'test'
ANALYSIS_NAME = 'test_separator'

CurrentModel = None
CurrentField = None
CurrentAnalysis = None

# Required to load separator_model.xml
class After(Process):
    def run(self, analysis):
        pass

    def impute(self):
        pass


def field_network_graph(model_xml, field_name):
    mf = ModelFile(model_xml, add_stream_components=False, use_class_path=False)
    field = mf.model.get_field(field_name)

    global CurrentModel
    global CurrentAnalysis
    global CurrentField

    CurrentModel = mf.model
    CurrentAnalysis = CurrentModel.get_analysis(ANALYSIS_NAME)
    CurrentField = field

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

    layout = go.Layout(title=f"Model: '{MODEL_XML}'", showlegend=False,
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

app.layout = html.Div([
    # Title
    html.Div([html.H1(f"OPGEE field '{FIELD_NAME}'")],
             className="row",
             style={'textAlign': "center"}),
    # define the row
    html.Div(
        className="row",
        children=[
             # middle graph component
            html.Div(
                className="eight columns",
                children=[dcc.Graph(id="my-graph",
                                    # figure=network_graph(YEAR, ACCOUNT),
                                    figure=field_network_graph(MODEL_XML, FIELD_NAME))],
            ),

            # right side two output component
            html.Div(
                className="four columns",
                children=[
                    html.Div(
                        className='twelve columns',
                        children=[
                            html.Button('Run model', id='run-button', n_clicks=0),
                            dcc.Markdown(id='model-status')
                        ],
                        style={'height': '100px'}),
                    html.Div(
                        className='twelve columns',
                        children=[
                            dcc.Markdown(d("""
                            **Hover Data**

                            Emissions and energy use
                            """)),
                            html.Pre(id='hover-data', style=styles['pre'])
                        ],
                        style={'height': '400px'}),

                    html.Div(
                        className='twelve columns',
                        children=[
                            dcc.Markdown(d("""
                            **Click Data**

                            Click on points in the graph.
                            """)),
                            html.Pre(id='click-data', style=styles['pre'])
                        ],
                        style={'height': '400px'})
                ]
            )
        ]
    )
])

# callback for left side components
@app.callback(
    dash.dependencies.Output('my-graph', 'figure'),
    [dash.dependencies.Input('my-range-slider', 'value'), dash.dependencies.Input('input1', 'value')])
def update_output(value,input1):
    return field_network_graph(MODEL_XML, FIELD_NAME)
    # to update the global variable of YEAR and ACCOUNT

# callback for right side components
@app.callback(
    dash.dependencies.Output('hover-data', 'children'),
    [dash.dependencies.Input('my-graph', 'hoverData')])
def display_hover_data(hoverData):
    if hoverData:
        proc_name = hoverData['points'][0]['text']
        proc = CurrentField.find_process(proc_name)
        rates, co2e = proc.get_emission_rates(CurrentAnalysis)
        # display values without all the Series stuff
        digits = 2
        values = '\n'.join([f"{name:4s} {round(value.m, digits)}" for name, value in rates.items()])
        return f"{proc_name}:\n{values}\nCO2e {round(co2e, digits)}"
    else:
        return ''

@app.callback(
    dash.dependencies.Output('model-status', 'children'),
    [dash.dependencies.Input('run-button', 'n_clicks')])
def update_output(n_clicks):
    if n_clicks:
        CurrentField.run(CurrentAnalysis)
        return "Model has been run"
    else:
        return f"Model has not been run"

@app.callback(
    dash.dependencies.Output('click-data', 'children'),
    [dash.dependencies.Input('my-graph', 'clickData')])
def display_click_data(clickData):
    return json.dumps(clickData, indent=2)



if __name__ == '__main__':
    app.run_server(debug=True)
