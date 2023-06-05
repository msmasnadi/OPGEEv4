#
# Classes to support user modification of built-in tables
#
# Author: Richard Plevin
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .core import elt_name, XmlInstantiable, OpgeeObject


class Cell(OpgeeObject):
    """
    Defines a replacement for a value provided in a built-in CSV file.
    """
    def __init__(self, row, col, value):
        super().__init__()

        self.row = row
        self.col = col
        self.value = value


class TableUpdate(XmlInstantiable):
    """
    Supports user-defined updates to built-in CSV data.
    """

    def __init__(self, name, cells):
        super().__init__(name)
        self.cells = cells

    @classmethod
    def from_xml(cls, elt, parent=None):
        sub_elts = elt.findall('Cell')
        cells = [Cell(e.attrib['row'], e.attrib['col'], e.text) for e in sub_elts]
        return TableUpdate(elt_name(elt), cells)
