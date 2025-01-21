from importlib.resources import read_text

def get_resource_content(filename):
    return read_text(__package__, filename)