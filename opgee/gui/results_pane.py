import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from ..log import getLogger

from .widgets import get_analysis_and_field, OpgeePane

_logger = getLogger(__name__)


class ResultsPane(OpgeePane):

    def get_layout(self, field, **kwargs):
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


    def add_callbacks(self):
        app = self.app
        model = self.model

        @app.callback(
            Output('ci-text', 'children'),
            Input('run-button', 'n_clicks'),
            Input('analysis-and-field', 'data'))
        def ci_text(n_clicks, analysis_and_field):
            analysis, field = get_analysis_and_field(model, analysis_and_field)

            ci = field.compute_carbon_intensity(analysis).m
            fn_unit = analysis.attr('functional_unit')
            en_basis = analysis.attr('energy_basis')
            return f"CI: {ci:0.2f} g CO2e/MJ {en_basis} of {fn_unit}"

        @app.callback(
            Output('ci-barchart', 'figure'),
            Input('run-button', 'n_clicks'),
            Input('analysis-and-field', 'data'))
        def ci_barchart(n_clicks, analysis_and_field):
            import pandas as pd
            import plotly.graph_objs as go

            analysis, field = get_analysis_and_field(model, analysis_and_field)

            fn_unit = analysis.attr('functional_unit')

            def total_ghgs(obj):
                return obj.emissions.data.sum(axis='columns')['GHG']

            # Show results for top-level aggregators and procs for the selected field
            top_level = [(obj.name, total_ghgs(obj)) for obj in field.aggs + field.procs]

            df = pd.DataFrame({"category": [pair[0] for pair in top_level],
                               "value": [pair[1] for pair in top_level],
                               "unit": [fn_unit] * len(top_level)})

            fig = go.Figure(data=[go.Bar(name=row.category, x=[row.unit], y=[row.value]) for idx, row in df.iterrows()],
                            layout=go.Layout(barmode='stack'))

            fig.update_layout(yaxis_title="g CO2 per MJ",  # doesn't render in latex: r'g CO$_2$ MJ$^{-1}$',
                              xaxis_title=f'Carbon Intensity of {fn_unit.title()}')

            return fig
