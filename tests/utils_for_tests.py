from io import StringIO
from opgee.config import pathjoin, getParam, setParam, readConfigFile
from opgee.model_file import ModelFile
from opgee.process import Process

class ProcA(Process):
    def run(self, analysis):
        pass

class ProcB(Process):
    def run(self, analysis):
        pass

class Before(Process):
    def run(self, analysis):
        pass

    def impute(self):
        pass

# Required to load opgee.xml and some test XML files
class After(Process):
    def run(self, analysis):
        pass


def path_to_test_file(filename):
    path = pathjoin(__file__, '..', f'files/{filename}', abspath=True)
    return path

def load_test_model(xml_file, use_default_model=False, stream_components=None, class_path=None):
    old_class_path = getParam('OPGEE.ClassPath')
    old_stream_comps = getParam('OPGEE.StreamComponents')
    project = getParam('OPGEE.DefaultProject')

    if class_path:
        setParam('OPGEE.ClassPath', path_to_test_file('user_processes.py'), section=project)

    if stream_components:
        setParam('OPGEE.StreamComponents', stream_components, section=project)

    xml_path = path_to_test_file(xml_file)

    mf = ModelFile(xml_path, use_default_model=use_default_model,
                   add_stream_components=bool(stream_components),
                   use_class_path=bool(class_path))

    if class_path:
        setParam('OPGEE.ClassPath', old_class_path, section=project)

    if stream_components:
        setParam('OPGEE.StreamComponents', old_stream_comps, section=project)

    return mf.model

def load_model_from_str(xml_str, use_default_model=False):
    mf = ModelFile.from_xml_string(xml_str, use_default_model=use_default_model)
    return mf.model

def tmpdir(*args):
    d = pathjoin(getParam('OPGEE.TempDir'), *args)
    return d

def load_config_from_string(text):
    stream = StringIO(text)
    readConfigFile(stream)

