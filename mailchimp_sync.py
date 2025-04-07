# mailchimp_sync.py

import hashlib
import json
import requests
from merge_map import MERGE_FIELDS
from config import MAILCHIMP_API_KEY, MAILCHIMP_LIST_ID, MAILCHIMP_SERVER_PREFIX
from utils import format_date, convert_bool, convert_autorenew
from cache_utils import get_cached_email, update_cache
from log_utils import append_log_entry

def sync_to_mailchimp(member, subscription, event_type, override_guid=False):
    member_id = str(member.get("id"))
    current_email = member.get("email")
    original_email = get_cached_email(member_id) or current_email

    print(f"📨 Using original email: {original_email}")
    if original_email != current_email:
        print(f"✳️ Email changed in Memberful: {original_email} → {current_email}")

    merge_fields = {
        MERGE_FIELDS["first_name"]: member.get("first_name", ""),
        MERGE_FIELDS["last_name"]: member.get("last_name", ""),
        MERGE_FIELDS["member_id"]: "USER DELETED" if override_guid else member_id,
        MERGE_FIELDS["signup_date"]: format_date(member.get("created_at")),
    }

    if subscription:
        merge_fields.update({
            MERGE_FIELDS["plan_name"]: subscription.get("plan_name") or subscription.get("subscription_plan", {}).get("name", ""),
            MERGE_FIELDS["plan_active"]: convert_bool(subscription.get("active")),
            MERGE_FIELDS["auto_renew"]: convert_autorenew(subscription.get("autorenew")),
            MERGE_FIELDS["expires_at"]: format_date(subscription.get("expires_at")),
        })

    payload = {
        "email_address": current_email,
        "status_if_new": "subscribed",
        "merge_fields": merge_fields
    }

    print("Payload being sent to Mailchimp:")
    print(json.dumps(payload, indent=2))

    try:
        contact_hash = hashlib.md5(original_email.lower().encode()).hexdigest()
        member_url = f"https://{MAILCHIMP_SERVER_PREFIX}.api.mailchimp.com/3.0/lists/{MAILCHIMP_LIST_ID}/members/{contact_hash}"

        # 1️⃣ Sync basic profile and merge fields
        response = requests.put(member_url, auth=("anystring", MAILCHIMP_API_KEY), json=payload)
        if response.status_code in [200, 201]:
            print(f"✅ Synced {original_email}: {response.status_code}")
            update_cache(member_id, current_email)
            append_log_entry(event_type, current_email, "success")
        else:
            print(f"❌ Failed to sync {original_email}: {response.status_code}")
            print("Mailchimp error response:")
            print(response.text)
            append_log_entry(event_type, current_email, "error")
            return

        # 2️⃣ Apply or remove "Payment Failed" tag
        tag_url = f"{member_url}/tags"
        tag_payload = {
            "tags": [
                {
                    "name": "Payment Failed",
                    "status": "active" if event_type == "order.failed" else "inactive"
                }
            ]
        }

        tag_response = requests.post(tag_url, auth=("anystring", MAILCHIMP_API_KEY), json=tag_payload)
        if tag_response.status_code not in [200, 204]:
            print(f"⚠️ Failed to update tags: {tag_response.status_code}")
            print(tag_response.text)

    except Exception as e:
        print(f"❌ Exception during Mailchimp sync: {e}")
        append_log_entry(event_type, current_email, "exception")
