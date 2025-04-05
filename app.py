from dotenv import load_dotenv
load_dotenv()

from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash
import os

auth = HTTPBasicAuth()

LOGS_USER = os.getenv("LOGS_USER")
LOGS_PASSWORD_HASH = os.getenv("LOGS_PASSWORD_HASH")

@auth.verify_password
def verify_password(username, password):
    if username == LOGS_USER and check_password_hash(LOGS_PASSWORD_HASH, password):
        return username

from flask import Flask, request, render_template, abort
import os
import json
from storage_utils import load_json
from datetime import datetime
import hmac
import hashlib
from config import MEMBERFUL_WEBHOOK_SECRET
from mailchimp_sync import sync_to_mailchimp
from cache_utils import load_cache, save_cache, get_cached_email
from log_utils import append_log_entry

app = Flask(__name__)
LOG_FILE = "webhook_logs.json"

def verify_signature(request):
    signature = request.headers.get("X-Memberful-Webhook-Signature")

    # Allow bypass for internal replays
    if signature == "REPLAY":
        return True

    if not signature:
        print("❌ Missing signature header")
        return False

    secret = MEMBERFUL_WEBHOOK_SECRET.encode()
    payload = request.get_data()
    computed = hmac.new(secret, payload, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed, signature):
        print("❌ Webhook signature does not match!")
        return False

    return True

# ✅ Register datetime formatting filter
@app.template_filter('datetimeformat')
def datetimeformat(value, mode='full'):
    try:
        dt = datetime.fromisoformat(value.replace("Z", ""))
        if mode == 'date':
            return dt.strftime('%d-%b-%Y')
        elif mode == 'time':
            return dt.strftime('%H:%M:%S')
        return dt.strftime('%d-%b-%Y %H:%M:%S')
    except Exception:
        return value

@app.route('/memberful-webhook', methods=['POST'])
def memberful_webhook():
    if not verify_signature(request):
        return abort(403, description="Invalid webhook signature")

    data = request.json
    event_type = data.get("event")

    print(f"Received webhook: {event_type}")
    print("Raw webhook payload:")
    print(data)

    # ✅ Special-case "order.failed" before the generic missing-email check
    if event_type == "order.failed":
        member = data.get("order", {}).get("member") or {}
        if not member.get("email"):
            print("⚠️ No email in order.failed event")
            return '', 200
        sync_to_mailchimp(member, None, event_type)
        append_log_entry(event_type, member["email"], "success", payload=data)
        return '', 200

    # Standard extract
    member = data.get("member") or data.get("subscription", {}).get("member") or {}
    subscription = data.get("subscription") or {}

    if not member.get("email") and event_type != "member.deleted":
        print("⚠️ Member object missing or has no email — skipping Mailchimp sync.")
        return '', 200

    # Handle normal sync events
    if event_type in [
        "member_signup", "member_updated",
        "subscription.created", "subscription.updated",
        "subscription.renewed", "subscription.activated",
        "subscription.expired"
    ]:
        sync_to_mailchimp(member, subscription, event_type)

        if event_type == "member_updated":
            member_id = member.get("id")
            current_email = member.get("email")
            cached_email = get_cached_email(member_id)
            changes = data.get("changed", {})
            if cached_email and cached_email != current_email:
                print(f"✳️ Email changed in Memberful: {cached_email} → {current_email}")
            append_log_entry(event_type, current_email, "success", diff=changes, payload=data)
        else:
            append_log_entry(event_type, member.get("email"), "success", payload=data)

    elif event_type == "subscription.deactivated":
        subscription_stub = {
            "active": False,
            "plan_name": subscription.get("plan_name") or subscription.get("subscription_plan", {}).get("name", ""),
            "autorenew": subscription.get("autorenew"),
            "expires_at": subscription.get("expires_at")
        }
        sync_to_mailchimp(member, subscription_stub, event_type)
        append_log_entry(event_type, member.get("email"), "success", payload=data)

    elif event_type == "subscription.deleted":
        member["email"] = member.get("email") or get_cached_email(member.get("id"))
        if not member["email"]:
            print("⚠️ No email found for deleted subscription")
        else:
            subscription_stub = {
                "active": False,
                "plan_name": "",
                "autorenew": None,
                "expires_at": None
            }
            sync_to_mailchimp(member, subscription_stub, event_type)
            append_log_entry(event_type, member["email"], "success", payload=data)

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
                sync_to_mailchimp(member_stub, subscription_stub, event_type, override_guid=True)
                append_log_entry(event_type, cached_email, "success", payload=data)

                cache = load_cache()
                cache.pop(str(member_id), None)
                save_cache(cache)
            else:
                print(f"⚠️ No cached email found for deleted member ID {member_id}")
        else:
            print("⚠️ No member ID in deleted webhook")

    return '', 200

@app.route('/logs', methods=['GET'])
@auth.login_required
def view_logs():
    logs = []
    try:
        logs = sorted(load_json(LOG_FILE), key=lambda x: x.get("timestamp", ""), reverse=True)
    except Exception as e:
        print(f"⚠️ Failed to load logs: {e}")
    return render_template("logs.html", logs=logs)

@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "ok"}, 200

@app.route('/replay-log', methods=['POST'])
@auth.login_required
def replay_log():
    data = request.get_json()
    if not data or "event" not in data:
        return "Missing payload or event", 400

    print(f"🔁 Replaying event: {data['event']}")

    with app.test_request_context(
        '/memberful-webhook',
        method='POST',
        json=data,
        headers={"X-Memberful-Webhook-Signature": "REPLAY"}
    ):
        return memberful_webhook()

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5050))  # Defaults to 5050 locally, uses PORT from env in prod
    app.run(host="0.0.0.0", port=port)
