from opgee.utils import pathjoin
from opgee.model import ModelFile

def path_to_test_file(filename):
    path = pathjoin(__file__, '..', f'files/{filename}', abspath=True)
    return path

def load_test_model(xml_file):
    xml_path = path_to_test_file(xml_file)
    mf = ModelFile(xml_path, add_stream_components=False, use_class_path=False)
    return mf.model
