#
# Classes to support user modification of built-in tables
#
from .core import elt_name, XmlInstantiable, OpgeeObject

class Cell(OpgeeObject):

    def __init__(self, row, col, value):
        super().__init__()

        self.row = row
        self.col = col
        self.value = value

class TableUpdate(XmlInstantiable):

    def __init__(self, name, cells):
        super().__init__(name)
        self.cells = cells

    @classmethod
    def from_xml(cls, elt):
        sub_elts = elt.findall('Cell')
        cells = [Cell(e.attrib['row'], e.attrib['col'], e.text) for e in sub_elts]
        return TableUpdate(elt_name(elt), cells)
