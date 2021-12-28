from opgee.config import pathjoin
from opgee.model import ModelFile
from opgee.process import Process, reload_subclass_dict

class ProcA(Process):
    def run(self, analysis):
        pass

class ProcB(Process):
    def run(self, analysis):
        pass

class ProcC(Process):
    def run(self, analysis):
        pass

def path_to_test_file(filename):
    path = pathjoin(__file__, '..', f'files/{filename}', abspath=True)
    return path

def load_test_model(xml_file, add_stream_components=False, use_class_path=False):
    reload_subclass_dict()
    xml_path = path_to_test_file(xml_file)
    mf = ModelFile(xml_path, add_stream_components=add_stream_components, use_class_path=use_class_path)
    return mf.model
