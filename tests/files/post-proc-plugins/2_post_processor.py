import os

from opgee.post_processor import PostProcessor

class PostProcessor_2(PostProcessor):
    results = []

    def __init__(self):
        pass

    @classmethod
    def clear(cls):
        cls.results.clear()

    def run(self, analysis, field, result):
        self.results.append(('plugin-2-data', result))

    def save(self, output_dir):
        path = os.path.join(output_dir, 'auto_loaded_post_proc_2.csv')
        with open(path, 'w') as f:
            for tag, value in self.results:
                f.write(f"{tag}, {value}\n")
