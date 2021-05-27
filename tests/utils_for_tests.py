from opgee.config import pathjoin
from opgee.model import ModelFile

def path_to_test_file(filename):
    path = pathjoin(__file__, '..', f'files/{filename}', abspath=True)
    return path

def load_test_model(xml_file, add_stream_components=False, use_class_path=False):
    xml_path = path_to_test_file(xml_file)
    mf = ModelFile(xml_path, add_stream_components=add_stream_components, use_class_path=use_class_path)
    return mf.model
