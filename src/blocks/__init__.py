import json
from os.path import join, dirname


def read_json(path):
    abs_path = join(dirname(__file__), path)
    with open(abs_path) as f:
        out = json.load(f)
    return out
