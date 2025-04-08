# merge_utils.py

from storage_utils import load_json

def get_merge_fields():
    return load_json("merge_map.json")
