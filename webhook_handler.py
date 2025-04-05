from flask import request
from mailchimp_sync import sync_to_mailchimp
from cache_utils import get_cached_email, load_cache, save_cache
from log_utils import append_log_entry
import json

def handle_webhook():
    data = request.json
    event_type = data.get("event")
    print(f"Received webhook: {event_type}")
    print("Raw webhook payload:")
    print(data)

    member = data.get("member") or data.get("subscription", {}).get("member") or {}
    subscription = data.get("subscription") or {}

    if not member.get("email") and event_type != "member.deleted":
        print("⚠️ Member object missing or has no email — skipping Mailchimp sync.")
        return '', 200

    if event_type in [
        "member_signup", "member_updated",
        "subscription.created", "subscription.updated",
        "subscription.renewed", "subscription.activated"
    ]:
        sync_to_mailchimp(member, subscription, event_type=event_type)

    elif event_type == "subscription.deactivated":
        subscription_stub = {
            "active": False,
            "plan_name": subscription.get("plan_name") or subscription.get("subscription_plan", {}).get("name", ""),
            "autorenew": subscription.get("autorenew"),
            "expires_at": subscription.get("expires_at")
        }
        sync_to_mailchimp(member, subscription_stub, event_type=event_type)

    elif event_type == "subscription.deleted":
        member["email"] = member.get("email") or get_cached_email(member.get("id"))
        if member["email"]:
            subscription_stub = {
                "active": False,
                "plan_name": "",
                "autorenew": None,
                "expires_at": None
            }
            sync_to_mailchimp(member, subscription_stub, event_type=event_type)
        else:
            print("⚠️ No email found for deleted subscription")

    elif event_type == "member.deleted":
        member_id = member.get("id")
        if member_id:
            cached_email = get_cached_email(member_id)
            if cached_email:
                member_stub = {
                    "email": cached_email,
                    "id": member_id,
                    "first_name": "",
                    "last_name": "",
                    "created_at": ""
                }
                subscription_stub = {
                    "active": False,
                    "plan_name": "",
                    "autorenew": None,
                    "expires_at": None
                }
                sync_to_mailchimp(member_stub, subscription_stub, event_type=event_type, override_guid=True)

                cache = load_cache()
                cache.pop(str(member_id), None)
                save_cache(cache)
            else:
                print(f"⚠️ No cached email found for deleted member ID {member_id}")
        else:
            print("⚠️ No member ID in deleted webhook")

    return '', 200
