import pydot
from .core import OpgeeObject, Process
from .utils import ipython_info

def add_subclasses(graph, cls):
    name = cls.__name__
    graph.add_node(pydot.Node(name, shape='box'))

    if cls == Process:
        return

    subs = cls.__subclasses__()
    for sub in subs:
        graph.add_edge(pydot.Edge(name, sub.__name__, color='black'))
        add_subclasses(graph, sub)

def write_class_diagram(pathname):
    graph = pydot.Dot('classes', graph_type='graph', bgcolor='white')
    add_subclasses(graph, OpgeeObject)
    graph.write_png(pathname)

    # if in a notebook, also display it directly
    if ipython_info() == 'notebook':
        from IPython.display import Image, display
        png = graph.create_png()
        display(Image(png))

def write_model_diagram(model, pathname):
    """
    Create a network graph from an OPGEE Model.

    :param model: (Model) a populated Model instance
    :param pathname: (str) the pathname of the PNG file to create
    :return: None
    """
    def name_of(obj):
        class_name = obj.__class__.__name__
        obj_name = obj.name
        return f"{class_name}({obj_name})" if obj_name else class_name

    def add_tree(graph, obj):
        name = name_of(obj)
        print(f"Adding node '{name}'")
        graph.add_node(pydot.Node(name, shape='box'))

        for child in obj.children():
            add_tree(graph, child)
            print(f"Adding edge('{name}', '{name_of(child)}')")
            graph.add_edge(pydot.Edge(name, name_of(child), color='black'))

    graph = pydot.Dot('model', graph_type='graph', bgcolor='white')
    add_tree(graph, model.analysis)
    print(f"Writing {pathname}")
    graph.write_png(pathname)
