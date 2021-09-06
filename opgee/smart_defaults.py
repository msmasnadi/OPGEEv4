from .core import OpgeeObject

class SmartDefault(OpgeeObject):
    """
    Defines the dependencies and logic for a single "Smart Default".
    """
    instances = {}      # SmartDefault instances keyed by attribute name

    def __init__(self, attr_name, func):
        """

        :param attr_name: (str) the name of the attribute set by this smart default
        :param requires: (list of str) names of attributes in the same Process or enclosing Field that this object depends on
        """
        super().__init__()
        self.attr_name = attr_name

        # The function to call to set this default. The function is called with two arguments: current Field and the
        # name of the attribute. This permits the Process developer to write a single function that handles multiple
        # attributes rather than writing separate functions for each.
        self.func = func    # func(Field, str)

        self.instances[attr_name] = self

    #
    # TBD: this should probably be called after calling all the _after_init() methods and we have
    # TBD: the entire model structure available. Need a way to detect whether user has set a value,
    # TBD: unless we set smart defaults first and then allow users to overwrite these. Perhaps have
    # TBD: calls to SmartDefault("name", func) at the top-level so the registration happens at load?
    #
    def set_defaults(self, field):
        """
        Run the smart default to set its attribute value for the given Field.

        :param field: (opgee.Field) the Field for which to set this attribute
        :return: the value set
        """
        ordered_defaults = []       # TBD: topographical sort

        for obj in ordered_defaults:
            attr_name = obj.attr_name
            value = obj.func(field, attr_name)

            # TBD: only if user hasn't provided a value?
            attr = field.attr(attr_name)
            attr.set_smart_default(value)
