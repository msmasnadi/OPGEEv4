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

def load_test_model(xml_file, add_stream_components=False, use_default_model=False,
                    use_class_path=False, class_path=None):
    project = None

    if class_path:
        use_class_path = True

        project = getParam('OPGEE.DefaultProject')
        setParam('OPGEE.ClassPath', path_to_test_file('user_processes.py'), section=project)

    xml_path = path_to_test_file(xml_file)

    mf = ModelFile(xml_path,
                   add_stream_components=add_stream_components,
                   use_class_path=use_class_path,
                   use_default_model=use_default_model)

    if class_path:
        setParam('OPGEE.ClassPath', '', section=project)  # avoid reloading user_processes.py

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

