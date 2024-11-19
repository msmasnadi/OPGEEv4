import os

from opgee.post_processor import PostProcessor

class SimplePostProcessor(PostProcessor):
    results = []

    def __init__(self):
        pass

    @classmethod
    def clear(cls):
        cls.results.clear()

    def run(self, analysis, field, result):
        """
        Append results to the class variable ``results``
        """
        self.results.append(('dummy-data', result))

    def save(self, output_dir):
        """
        Write results to a CSV file
        """
        path = os.path.join(output_dir, 'simple_post_processor.csv')
        with open(path, 'w') as f:
            for tag, value in self.results:
                f.write(f"{tag}, {value}\n")
