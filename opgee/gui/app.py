#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, ClientsideFunction
from ..model_file import ModelFile
from ..log import getLogger

from .widgets import get_analysis_and_field, horiz_space, pulldown_style, label_style

_logger = getLogger(__name__)


# # styles: for right side hover/click component
# styles = {
#     'pre': {
#         'border': 'thin lightgrey solid',
#         'overflowX': 'scroll'
#     }
# }

def app_layout(app, model, analysis):
    analysis_names = [analysis.name for analysis in model.analyses()]

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
                    html.Span(f"{model.pathnames}"),
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


def main(args):
    from ..version import VERSION
    from .process_pane import ProcessPane
    from .settings_pane import SettingsPane
    from .results_pane import ResultsPane

    use_default_model = not args.no_default_model

    mf = ModelFile(args.model_file, add_stream_components=args.add_stream_components,
                   use_class_path=args.use_class_path, use_default_model=use_default_model)
    model = mf.model
    analysis_name = args.analysis

    initial_analysis = model.get_analysis(analysis_name)

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
    # N.B. use "app.config['suppress_callback_exceptions'] = True" to not need to call tab-layout fns in this layout def

    process_pane  = ProcessPane(app, model)
    settings_pane = SettingsPane(app, model)
    results_pane  = ResultsPane(app, model)

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
        settings_pane.generate_settings_callback(analysis, field)
        return dict(analysis=analysis_name, field=field_name)

    @app.callback(
        Output('run-model-status', 'children'),
        Input('run-button', 'n_clicks'),
        State('analysis-and-field', 'data'))
    def update_output(n_clicks, analysis_and_field):
        if n_clicks:
            analysis, field = get_analysis_and_field(model, analysis_and_field)
            field.resolve_process_choices()
            field.run(analysis)
            field.report(analysis)
            return "Model has been run"
        else:
            return "Model has not been run"

    @app.callback(
        Output('tab-content', 'children'),
        Input('tabs', 'value'),
        Input('analysis-and-field', 'data'),
    )
    def render_content(tab, analysis_and_field):
        analysis, field = get_analysis_and_field(model, analysis_and_field)

        if tab == 'processes':
            return process_pane.get_layout(field)

        elif tab == 'settings':
            return settings_pane.get_layout(field)

        elif tab == 'results':
            return results_pane.get_layout(field)

    # @app.callback(
    #     Output('xxxx', 'children'),
    #     Input('network-layout', 'mouseoverEdgeData')
    # )
    # def mouseoverStream(data):
    #     if data:
    #         return 'whatever'

    app.run_server(debug=True)
