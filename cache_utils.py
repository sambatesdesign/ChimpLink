# cache_utils.py

from config import CACHE_FILE
from storage_utils import load_json, save_json

def load_cache():
    return load_json(CACHE_FILE)

def save_cache(cache):
    save_json(CACHE_FILE, cache)

def get_cached_email(member_id):
    cache = load_cache()
    return cache.get(str(member_id))

def update_cache(member_id, email):
    cache = load_cache()
    cache[str(member_id)] = email
    save_cache(cache)
