#
# Support for post-processing plugins that run after a Field has been run.
#
# Author: Richard Plevin
# Copyright (c) 2024 the author and RMI
# See the https://opensource.org/licenses/MIT for license details.
#
from .core import OpgeeObject
from .error import AbstractMethodError, McsUserError

class PostProcessor(OpgeeObject):
    """
    Abstract base class for post-processing plugins. Subclasses must implement
    the ``run`` method to perform the post-processing, and they can optionally
    implement the ``save`` method to save the post-processed data to a file.
    """

    # List subclass instances in order defined on the command-line
    instances = []

    def __init__(self):
        pass

    def run(self, analysis, field, results):
        # to avoid an import cycle, args have no type specs

        """
        [Required method to be implemented by subclasses.]

        Run the desired post-processing.

        :param analysis: (Analysis) the Analysis applied to run the Field
        :param field: (Field) the Field that was run
        :param results: (FieldResult) the standard OPGEE results after running
          the Field.
        :return: nothing
        """
        raise AbstractMethodError(self.__class__, 'PostProcessor.run')

    def save(self, output_dir):
        """
        [Optional method to be implemented by subclasses.]

        Save the data accumulated by this plugin to a file.

        :param output_dir: (str) the directory to save the data to
        :return: nothing
        """
        pass

    @classmethod
    def clear(cls):
        """
        [Optional method to be implemented by subclasses]

        Clear any class variable state that should not persist between
        model runs. This describes class variables in the subclasses of
        ``PostProcessor``: the plugin instances stored here *should* persist.

        :return: nothing
        """
        pass

    @classmethod
    def decache(cls):
        cls.instances.clear()

    @classmethod
    def load_plugin(cls, path):
        """
        Load the plugin at the given ``path``, which must be a subclass
        of PostProcessor. Only one subclass should defined in this file;
        if more than one appears in the file, which one gets loaded is
        not well-defined.

        :return: nothing
        """
        import inspect
        import os.path
        from .utils import loadModuleFromPath

        if not os.path.exists(path):
            raise McsUserError(f"Path to plugin '{path}' does not exist.")

        module = loadModuleFromPath(path)

        # Find the class, create an instance, and store it in cls.instances
        for name, subcls in inspect.getmembers(module):
            # Subclasses import PostProcessor, but we want only proper subclasses, not PostProcessor
            if subcls != PostProcessor and inspect.isclass(subcls) and issubclass(subcls, PostProcessor):
                instance = subcls()
                cls.instances.append(instance)
                return instance

        raise McsUserError(f"No subclass of PostProcessor found in module '{path}'")

    @classmethod
    def run_post_processors(cls, analysis, field, result):
        for instance in cls.instances:
            instance.run(analysis, field, result)

    @classmethod
    def save_post_processor_results(cls, output_dir):
        for instance in cls.instances:
            instance.save(output_dir)
            instance.clear()
