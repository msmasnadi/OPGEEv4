import dash_core_components as dcc
import dash_html_components as html

def radio_items(title, options, default, direction='v', id=None):
    """
    Create dcc.RadioItems with a more convenient API.

    :param title: (str) text to place above the radio buttons
    :param options: (dict) keys are display string; values are return string
    :param default: (str) the default value (must be one of the values in the dict)
    :param direction: (str) 'h' for horizontal, 'v' for vertical
    :param id: (str) id for this button array. If missing, `title` is used.
    :return:
    """
    options = [dict(label=label, value=value) for label, value in options.items()]
    label_style = {'display': 'inline-block', 'margin': '4px'} if direction == 'h' else None

    id = id or title

    layout = html.Div(
        children=[
            html.Span(title, style={'font-weight': 'bold'}),
            dcc.RadioItems(options=options, value=default, labelStyle=label_style, persistence=True, id=id),
        ]
    )

    return layout
