import dash_core_components as dcc
import dash_html_components as html
import dash_cytoscape as cyto
from dash.dependencies import Input, Output, State
import dash_table
from textwrap import dedent as d

from .. import Process
from ..log import getLogger
from .widgets import get_analysis_and_field, gui_switches, OpgeePane

_logger = getLogger(__name__)


class ProcessPane(OpgeePane):

    def get_layout(self, field, show_streams_to_env=False, show_stream_contents=False, show_disabled_procs=False,
               layout_name='breadthfirst'):
        # the main row
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
                                        show_disabled_procs=show_disabled_procs,
                                        layout_name=layout_name)
                ],
                style={
                    'resize': 'vertical',
                    # 'overflow': 'auto',
                    # 'height': '35%',
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
                                **Stream Data** (tonne/day)
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


    def add_callbacks(self):
        app = self.app
        model = self.model

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
                    components = str(nonzero.astype(float)) if len(nonzero) else '<empty stream>'

                contents = '\n          '.join(stream.contents)
                text = f"Name: {name}\nContains: {contents}\n{components}"
                return html.Pre(text)

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
                    details = html.Details(children=[html.Summary(html.B(agg.name))], style=style)
                    elt.children.append(details)
                    add_children(agg, details)

                if container.procs:
                    enabled_procs = [proc for proc in container.procs if proc.is_enabled]
                    sorted_procs = sorted(enabled_procs, key=lambda p: p.name)
                    div = html.Div(style=style,
                                   children=[emissions_table(analysis, sorted_procs)])
                    elt.children.append(div)

            item = html.Details(open=True, children=[html.Summary("Process Emissions")])
            add_children(field, item)
            return item

        @app.callback(
            Output('field-network-graph-div', 'children'),
            Input('show-streams-to-env', 'value'),
            Input('show-stream-contents', 'value'),
            Input('show-disabled-procs', 'value'),
            Input('graph-layout-selector', 'value'),
            State('analysis-and-field', 'data'),
        )
        def redraw_network_graph(show_streams_to_env, show_stream_contents, show_disabled_procs,
                                 layout_name, analysis_and_field):
            analysis, field = get_analysis_and_field(model, analysis_and_field)
            return field_network_graph(field,
                                       show_streams_to_env=show_streams_to_env,
                                       show_stream_contents=show_stream_contents,
                                       show_disabled_procs=show_disabled_procs,
                                       layout_name=layout_name)


# Load extra layouts
# cyto.load_extra_layouts()   # required for cose-bilkent

def field_network_graph(field, show_streams_to_env=False, show_stream_contents=False, show_disabled_procs=False, layout_name='breadthfirst'):
    nodes = [{'data': {'id': name, 'label': name},
              'classes': ('enabled-node' if proc.enabled else 'disabled-node')} for name, proc in field.process_dict.items()
             if show_disabled_procs or proc.enabled]  # , 'size': 150  didn't work

    edges = [{'data': {'id': name, 'source': s.src_name, 'target': s.dst_name, 'contents': ', '.join(s.contents)},
              'classes': ('enabled-edge' if (s.dst_proc.enabled and s.src_proc.enabled) else 'disabled-edge')} for
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
            'name': layout_name,
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
                'selector': '.disabled-node',
                'style': {
                    'background-color': 'lightgray',
                }
            },
            {
                'selector': 'edge',
                'style': {
                    'curve-style': 'bezier',
                    # 'arrow-scale': 1.5,
                    # 'mid-target-arrow-color': edge_color,
                    # 'mid-target-arrow-shape': 'triangle',
                    'target-arrow-shape': 'triangle',
                    'target-arrow-color': edge_color,
                    'line-color': edge_color,
                    'line-opacity': 0.60,
                    'width': 1,
                    'target-distance-from-node': 1,  # stop just short of the node
                    'source-distance-from-node': 1,

                    # "overlay-padding": "30px",
                    'label': 'data(contents)',
                    'text-opacity': 0.6 if show_stream_contents else 0.0,
                    'text-rotation': 'autorotate',
                    'text-margin-y': -10,
                    'text-margin-x': 7,
                    'text-background-color': 'blue',
                    "font-size": "14px",
                },
            },
            {
                'selector': '.disabled-edge',
                'style': {
                    'target-arrow-color': 'gray',
                    'line-color': 'gray',
                }
            },
        ]
    )

    return layout


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
