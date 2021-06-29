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

    attr_options('Analysis')

    layout = html.Div(
        children=[
            html.Span(title, style={'font-weight': 'bold'}),
            dcc.RadioItems(options=options, value=default, labelStyle=label_style, persistence=True, id=id),
        ]
    )

    return layout

def attr_options(class_name, direction='v'):
    from ..attributes import AttrDefs

    attr_defs = AttrDefs.get_instance()
    class_attrs = attr_defs.classes.get(class_name)
    if not class_attrs:
        return ''

    option_dict = class_attrs.option_dict
    if len(option_dict) == 0:
        return ''

    # attr_dict   = class_attrs.attr_dict

    label_style = {'display': 'inline-block', 'margin': '4px'} if direction == 'h' else None

    details = html.Details([
        html.Summary(class_name, style={'font-weight': 'bold', 'font-size': '14px'})
    ])

    layout = html.Div(
        children=[
            # html.Div(class_name, style={'font-weight': 'bold', 'font-size': '14px'})
            details
        ],
        className='row',
        style={
            'text-align': 'left',
            'background-color': 'aliceblue',
            'border-radius': '4px',
            'border': '1px solid',
            'padding': '5px',
            'margin': '2px',
        }

    )

    children = details.children

    for title, opt in option_dict.items():
        options = [dict(label=label, value=value) for value, label, desc in opt.options]

        radio = html.Div(
            children=[
                html.Span(title, style={'font-weight': 'bold'}),
                dcc.RadioItems(options=options, value=opt.default, labelStyle=label_style,
                               persistence=True, id=title),
            ],
            className="one column",
            style={'text-align': 'left'}
        )
        children.append(radio)

    return layout

