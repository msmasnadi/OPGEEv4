#
# Classes to support user modification of built-in tables
#
from .core import instantiate_subelts, elt_name, XmlInstantiable

class Cell(XmlInstantiable):

    def __init__(self, row, col, value):
        name = None
        super().__init__(name)

        self.row = row
        self.col = col
        self.value = value

    @classmethod
    def from_xml(cls, elt):
        attr = elt.attrib
        return Cell(attr['row'], attr['col'], elt.text)


class TableUpdate(XmlInstantiable):

    def __init__(self, name, cells):
        super().__init__(name)
        self.cells = cells

    def apply(self, tbl_mgr):
        pass

    @classmethod
    def from_xml(cls, elt):
        cells = instantiate_subelts(elt, Cell)
        return TableUpdate(elt_name(elt), cells)

