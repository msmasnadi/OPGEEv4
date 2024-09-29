#
# Support for post-processing plugins that run after a Field has been run.
#
# Author: Richard Plevin
# Copyright (c) 2024 the author and RMI
# See the https://opensource.org/licenses/MIT for license details.
#

from .analysis import Analysis
from .core import OpgeeObject, Timer
from .error import AbstractMethodError
from .field import Field, FieldResult

class PostProcessor(OpgeeObject):
    """
    Abstract base class for post-processing plugins. Subclasses must implement
    the ``run`` method to perform the post-processing, and they can optionally
    implement the ``save`` method to save the post-processed data to a file.
    """

    # Track instances in order defined on the command-line, so we can
    # run them in the intended sequence
    instances = []

    def __init__(self):
        pass

    @classmethod
    def clear(cls):
        """
        [Optional method to be implemented by subclasses]

        Clear any state stored in class variables that should not persist between
        model runs. This describes class variables in the subclasses of
        ``PostProcessor``: the plugin instances stored here *should* persist.

        :return: nothing
        """
        pass

    def run(self, analysis: Analysis, field: Field, results: FieldResult):
        """
        [Required method to be implemented by subclasses.]

        Run the desired post-processing.

        :param analysis: (Analysis) the Analysis applied to run the Field
        :param field: (Field) the Field that was run
        :param results: (FieldResult) the standard OPGEE results after running
          the Field.
        :return: nothing
        """
        raise AbstractMethodError(PostProcessor, 'run')

    def save(self):
        """
        [Optional method to be implemented by subclasses.]

        Save the data accumulated by this plugin to a file.

        :return: nothing
        """
        pass
