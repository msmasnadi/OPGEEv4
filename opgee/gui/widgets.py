import dash_core_components as dcc
import dash_html_components as html
from ..core import magnitude
from ..error import OpgeeException

int_pattern = r'^\s*\d+\s*$'
float_pattern = r'^\s*((\d+).?(\d*)|(\d*).?(\d+))\s*$'

number_pattern = {'int': int_pattern, 'float': float_pattern}

binary_options = [dict(label='Yes', value=1), dict(label='No', value=0)]

def attr_inputs(class_name, direction='h'):
    from ..attributes import AttrDefs

    attr_defs = AttrDefs.get_instance()
    class_attrs = attr_defs.classes.get(class_name)
    if not class_attrs:
        return ''

    attr_dict = class_attrs.attr_dict

    details = html.Details(
        children=[
            html.Summary(class_name, style={'font-weight': 'bold', 'font-size': '14px'})
        ]
    )
    det_children = details.children

    radio_label_style = {'display': 'inline', 'margin-right': '8px'} if direction == 'h' else None  # , 'margin': '4px'

    for attr_name in sorted(attr_dict.keys(), key=str.casefold):
        id = f"{class_name}:{attr_name}"
        # print(f"Layout for input '{id}'")

        attr_def = attr_dict[attr_name]
        title = attr_name
        pytype = attr_def.pytype

        if pytype == 'binary':
            # noinspection PyCallingNonCallable
            input = dcc.RadioItems(id=id, options=binary_options, value=attr_def.default,
                                   labelStyle=radio_label_style,
                                   style={'display': 'inline-block', 'width': "45%"},
                                   persistence=True)

        elif attr_def.option_set:
            option_dict = class_attrs.option_dict
            if len(option_dict) == 0:
                raise OpgeeException(f'Options for option set {attr_def.option_set} are undefined')

            opt = option_dict[attr_def.option_set]
            options = [dict(label=label, value=value) for value, label, desc in opt.options]

            # noinspection PyCallingNonCallable
            input = dcc.RadioItems(id=id, options=options, value=opt.default,
                                   labelStyle=radio_label_style,
                                   style={'display': 'inline-block', 'width': "45%"},
                                   persistence=True)

        else:
            input_type = 'text' if (pytype is None or pytype == 'str') else 'number'
            # noinspection PyCallingNonCallable
            input = dcc.Input(id=id, type=input_type, debounce=True,
                              value=magnitude(attr_def.default),
                              pattern=number_pattern.get(pytype))

            unit = f"({attr_def.unit}) " if attr_def.unit else ''
            title = f"{attr_name} {unit}"

        # noinspection PyCallingNonCallable
        div = html.Div(
            children=[
                html.Div(title, style={
                    'font-weight': 'bold',
                    'width': '45%',
                    'display': 'inline-block',
                    'text-align': 'right',
                    'margin-right': '4px',
                }),
                input
            ],
            style={'margin-left': '4px', 'padding': '2px'}
        )

        det_children.append(div)

    # noinspection PyCallingNonCallable
    layout = html.Div(
        children=[details],
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
    return layout

def gui_switches():
    radio_label_style = {'display': 'inline', 'margin-right': '2px'}
    radio_options = [dict(label='Show', value=1), dict(label='Hide', value=0)]

    options = [
        ('Streams to Environment', 'show-streams-to-env', 0),
        ('Stream contents', 'show-stream-contents', 0),
        ('Disabled procs', 'show-disabled-procs', 0)
    ]

    outer_div = html.Div(children=[])
    children = outer_div.children

    # noinspection PyCallingNonCallable
    for title, id, value in options:
        span = html.Span(
            children=[
                html.Div(title + ':', style={
                    'font-weight': 'bold',
                    'display': 'inline',
                    'text-align': 'right',
                    'margin-left': '15px',
                }),

                dcc.RadioItems(id=id, options=radio_options, value=value,
                               labelStyle=radio_label_style,
                               style={'display': 'inline'},
                               persistence=True)
            ],
            # style={'padding': '1px'}
        )

        children.append(span)

    return outer_div
