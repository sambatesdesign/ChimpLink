# config.py

import os
from dotenv import load_dotenv

# Load environment variables from a .env file (useful for local dev)
load_dotenv()

MAILCHIMP_API_KEY = os.environ.get("MAILCHIMP_API_KEY")
MAILCHIMP_LIST_ID = os.environ.get("MAILCHIMP_LIST_ID")
MAILCHIMP_SERVER_PREFIX = os.environ.get("MAILCHIMP_SERVER_PREFIX")  # e.g., 'us10'
MEMBERFUL_WEBHOOK_SECRET = os.environ.get("MEMBERFUL_WEBHOOK_SECRET")

LOG_FILE = "webhook_logs.json"
CACHE_FILE = "member_email_cache.json"

APP_ENV = os.environ.get("APP_ENV", "local")
IS_PRODUCTION = APP_ENV == "production"
