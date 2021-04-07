import pydot
from .core import OpgeeObject
from .utils import ipython_info

def add_subclasses(graph, cls):
    name = cls.__name__
    graph.add_node(pydot.Node(name, shape='box'))

    subs = cls.__subclasses__()
    for sub in subs:
        graph.add_edge(pydot.Edge(name, sub.__name__, color='black'))
        add_subclasses(graph, sub)

def write_class_diagram(pathname):
    graph = pydot.Dot('my_graph', graph_type='graph', bgcolor='white')
    add_subclasses(graph, OpgeeObject)
    graph.write_png(pathname)

    # if in a notebook, also display it directly
    if ipython_info() == 'notebook':
        from IPython.display import Image, display
        png = graph.create_png()
        display(Image(png))

if __name__ == '__main__':
    write_class_diagram("/tmp/class_diagram.png")
