#!/usr/bin/env python3
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, ClientsideFunction

def app_layout(app):

    label_style = {
        'font-weight': 'bold'
    }

    # noinspection PyCallingNonCallable
    layout = html.Div([
        dcc.Store(id='analysis-and-field', storage_type='session'),

        # TBD: Experiment to see if client-side function fixes graph resizing problem, per
        # https://stackoverflow.com/questions/55462861/dash-dynamic-layout-does-not-propagate-resized-graph-dimensions-until-window-i
        # html.Div(id="output-clientside"),

        html.Div([
            html.H1(app.title),

            html.Div([
                html.Center([
                    html.Span("Model: ", style=label_style),
                    html.Span("Not a real model"),
                ]),
                html.Br(),

                html.Button('Run model', id='run-button', n_clicks=0),
                dcc.Markdown(id='run-model-status'),
            ],
            # style = {'height': '130px'}
            ),
        ], style={'textAlign': 'center'}
        ),
    ])
    return layout


def main():
    # import the css template, and pass the css template into dash
    external_stylesheets = [
        # 'https://codepen.io/chriddyp/pen/bWLwgP.css'
    ]
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
    app.config['suppress_callback_exceptions'] = True
    app.title = "Test App"

    # TBD: use "app.config['suppress_callback_exceptions'] = True" to not need to call tab-layout fns in this layout def

    app.layout = app_layout(app)

    # per https://stackoverflow.com/questions/55462861/dash-dynamic-layout-does-not-propagate-resized-graph-dimensions-until-window-i
    app.clientside_callback(
        ClientsideFunction(namespace="clientside", function_name="resize"),
        Output("output-clientside", "children"),
        [Input("network-layout", "figure")],
    )

    @app.callback(
        Output('run-model-status', 'children'),
        Input('run-button', 'n_clicks'),
        State('analysis-and-field', 'data'))
    def update_output(n_clicks, analysis_and_field):
        if n_clicks:
            return "Model has been run"
        else:
            return "Model has not been run"

    app.run_server(debug=True)

main()
