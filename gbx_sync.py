# gbx_sync.py

import hashlib
import json
import requests
from config import MAILCHIMP_API_KEY, MAILCHIMP_LIST_ID, MAILCHIMP_SERVER_PREFIX
from log_utils import append_log_entry
from storage_utils import load_json

def sync_gbx_profile_to_mailchimp(payload):
    try:
        email = payload.get("email")
        if not email:
            raise ValueError("Missing email in GBX profile payload")

        contact_hash = hashlib.md5(email.lower().encode()).hexdigest()
        member_url = f"https://{MAILCHIMP_SERVER_PREFIX}.api.mailchimp.com/3.0/lists/{MAILCHIMP_LIST_ID}/members/{contact_hash}"

        # ⬇️ Load latest GBX mapping from JSON
        merge_map = load_json("merge_map.json")
        gbx_map = merge_map.get("GBX_PROFILE_FIELDS", {})

        merge_fields = {}
        for key, merge_tag in gbx_map.items():
            value = payload.get(key)
            if value is not None:
                merge_fields[merge_tag] = value

        mc_payload = {
            "email_address": email,
            "status_if_new": "subscribed",
            "merge_fields": merge_fields
        }

        print("📬 Syncing GBX profile to Mailchimp:")
        print(json.dumps(mc_payload, indent=2))

        response = requests.put(
            member_url,
            auth=("anystring", MAILCHIMP_API_KEY),
            json=mc_payload
        )

        if response.status_code in [200, 201]:
            print(f"✅ GBX profile synced for {email}")
            append_log_entry("gbx_profile_sync", email, "success", payload=payload)
        else:
            print(f"❌ Mailchimp error {response.status_code}: {response.text}")
            append_log_entry("gbx_profile_sync", email, "error", payload=payload)

    except Exception as e:
        print(f"❌ Error syncing GBX profile: {e}")
        append_log_entry("gbx_profile_sync", payload.get("email", "unknown"), "exception", payload=payload)
