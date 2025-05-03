import requests
import time
import random
import hashlib
import json
import hmac
from dotenv import load_dotenv
load_dotenv()
from config import (
    MAILCHIMP_API_KEY,
    MAILCHIMP_LIST_ID,
    MAILCHIMP_SERVER_PREFIX,
    MEMBERFUL_WEBHOOK_SECRET,
)

WEBHOOK_URL = 'https://chimplink.gbxglobal.org/memberful-webhook'
#WEBHOOK_URL = 'http://localhost:5050/memberful-webhook'
MAILCHIMP_BASE = f'https://{MAILCHIMP_SERVER_PREFIX}.api.mailchimp.com/3.0'
HEADERS = {"Authorization": f"apikey {MAILCHIMP_API_KEY}"}


def sign_payload(payload: dict) -> dict:
    body = json.dumps(payload).encode()
    signature = hmac.new(
        MEMBERFUL_WEBHOOK_SECRET.encode(), body, digestmod="sha256"
    ).hexdigest()
    return {
        "X-Memberful-Webhook-Signature": signature,
        "Content-Type": "application/json"
    }


def send_webhook(event_type, payload):
    payload["event"] = event_type
    headers = sign_payload(payload)
    response = requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(payload))
    print(f"📤 Sent {event_type} webhook → Status: {response.status_code}")
    return response


def get_mailchimp_merge_fields(email):
    email_hash = hashlib.md5(email.lower().encode()).hexdigest()
    url = f"{MAILCHIMP_BASE}/lists/{MAILCHIMP_LIST_ID}/members/{email_hash}"
    res = requests.get(url, headers=HEADERS)
    return res.json().get("merge_fields", {})


def get_mailchimp_tags(email):
    email_hash = hashlib.md5(email.lower().encode()).hexdigest()
    url = f"{MAILCHIMP_BASE}/lists/{MAILCHIMP_LIST_ID}/members/{email_hash}/tags"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        return [tag["name"] for tag in res.json().get("tags", [])]
    return []


def verify_merge_fields(email, expected_fields):
    print(f"🔍 Verifying Mailchimp fields for {email}")
    merge_fields = get_mailchimp_merge_fields(email)
    for field, expected_value in expected_fields.items():
        actual = merge_fields.get(field)
        if str(actual) != str(expected_value):
            print(f"❌ {field} = {actual} (expected: {expected_value})")
        else:
            print(f"✅ {field} = {actual}")
    print("-" * 60)
    input("🔎 Press Enter to continue to the next step...")


def verify_tag_present(email, tag_name):
    print(f"🔍 Verifying Mailchimp tag '{tag_name}' for {email}")
    tags = get_mailchimp_tags(email)
    if tag_name in tags:
        print(f"✅ Tag '{tag_name}' is present")
    else:
        print(f"❌ Tag '{tag_name}' NOT found")
    print("-" * 60)
    input("🔎 Press Enter to continue to the next step...")


def verify_email_change(old_email, new_email):
    print(f"🔁 Verifying email change {old_email} → {new_email}")
    old_hash = hashlib.md5(old_email.lower().encode()).hexdigest()
    new_hash = hashlib.md5(new_email.lower().encode()).hexdigest()

    old_url = f"{MAILCHIMP_BASE}/lists/{MAILCHIMP_LIST_ID}/members/{old_hash}"
    new_url = f"{MAILCHIMP_BASE}/lists/{MAILCHIMP_LIST_ID}/members/{new_hash}"

    old_res = requests.get(old_url, headers=HEADERS)
    new_res = requests.get(new_url, headers=HEADERS)

    if old_res.status_code == 404:
        print("✅ Old email contact correctly removed")
    else:
        print(f"❌ Old email still exists! ({old_res.status_code})")

    if new_res.status_code == 200:
        print("✅ New email contact updated correctly")
    else:
        print(f"❌ New email not found! ({new_res.status_code})")

    print("-" * 60)
    input("🔎 Press Enter to continue to the next step...")


def permanently_delete_contact(email):
    email_hash = hashlib.md5(email.lower().encode()).hexdigest()
    url = f"{MAILCHIMP_BASE}/lists/{MAILCHIMP_LIST_ID}/members/{email_hash}"
    res = requests.delete(url, headers=HEADERS)
    print(f"🧹 Deleted {email} → Status: {res.status_code}")


def run_verified_test(unique_id):
    email = f"Mazespacedev{unique_id}@gmail.com"
    new_email = f"Mazespacedev{unique_id}CHANGED@gmail.com"
    first_name = "Testy"
    last_name = "McTester"
    member_id = 7000000 + unique_id
    created_at = "2023-01-01T00:00:00Z"

    # Step 1: member_signup
    send_webhook("member_signup", {
        "member": {
            "id": member_id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "created_at": created_at
        }
    })
    verify_merge_fields(email, {
        "FNAME": first_name,
        "LNAME": last_name,
        "MMERGE13": str(member_id),
        "MMERGE12": "2023-01-01"
    })

    # Step 2: subscription.created
    send_webhook("subscription.created", {
        "subscription": {
            "plan_name": "Starter Plan",
            "expires_at": "2025-04-02T00:00:00Z",
            "autorenew": True,
            "active": True,
            "member": {
                "id": member_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "created_at": created_at
            }
        }
    })
    verify_merge_fields(email, {
        "MMERGE7": "Starter Plan",
        "MMERGE8": "Yes",
        "MMERGE9": "On",
        "MMERGE10": "2025-04-02"
    })

    # Step 4: subscription.updated (upgrade/downgrade)
    send_webhook("subscription.updated", {
        "subscription": {
            "subscription_plan": {
                "name": "Pro Plan"
            },
            "autorenew": True,
            "active": True,
            "expires_at": "2026-04-02T00:00:00Z",
            "member": {
                "id": member_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "created_at": created_at
            }
        }
    })
    verify_merge_fields(email, {
        "MMERGE7": "Pro Plan",
        "MMERGE8": "Yes",
        "MMERGE10": "2026-04-02"
    })

    # Step 5: member_updated (email change)
    send_webhook("member_updated", {
        "member": {
            "id": member_id,
            "email": new_email,
            "first_name": first_name,
            "last_name": last_name,
            "created_at": created_at
        },
        "changed": {
            "email": [email, new_email]
        }
    })
    verify_email_change(email, new_email)

    # Step 6: subscription.expired
    send_webhook("subscription.expired", {
        "subscription": {
            "active": False,
            "autorenew": False,
            "expires_at": "2026-04-02T00:00:00Z",
            "subscription_plan": {
                "name": "Pro Plan"
            },
            "member": {
                "id": member_id,
                "email": new_email,
                "first_name": first_name,
                "last_name": last_name,
                "created_at": created_at
            }
        }
    })
    verify_merge_fields(new_email, {
        "MMERGE8": "No",
        "MMERGE9": "Off"
    })

    # Final cleanup
    cleanup = input("🧼 Delete this contact from Mailchimp? (y/n): ")
    if cleanup.lower() == "y":
        permanently_delete_contact(new_email)

if __name__ == "__main__":
    unique_id = random.randint(1000, 9999)
    run_verified_test(unique_id)
