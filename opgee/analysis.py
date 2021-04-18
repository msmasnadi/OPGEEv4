from .core import Container, elt_name, subelt_text, instantiate_subelts
from .field import Field

class Analysis(Container):
    def __init__(self, name, functional_unit=None, energy_basis=None,
                 variables=None, settings=None, streams=None, fields=None):
        super().__init__(name)

        # Global settings
        self.functional_unit = functional_unit
        self.energy_basis = energy_basis
        self.variables = variables   # dict of standard variables
        self.settings  = settings    # user-controlled settings
        self.streams   = streams     # define these here to avoid passing separately?
        self.field_dict = self.adopt(fields, asDict=True)

    def children(self):
        return self.field_dict.values()     # N.B. returns an iterator

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Analysis> element
        :return: (Analysis) instance populated from XML
        """
        name = elt_name(elt)
        fn_unit  = subelt_text(elt, 'FunctionalUnit', with_unit=False) # schema requires one of {'oil', 'gas'}
        en_basis = subelt_text(elt, 'EnergyBasis', with_unit=False)    # schema requires one of {'LHV', 'HHV'}
        fields = instantiate_subelts(elt, Field)

        # TBD: variables and settings
        obj = Analysis(name, functional_unit=fn_unit, energy_basis=en_basis, fields=fields)
        return obj
