from dotenv import load_dotenv
load_dotenv()

from forms import LoginForm
import os
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from flask import (
    Flask, request, render_template, redirect, url_for,
    session, abort, send_from_directory, jsonify
)
from werkzeug.security import check_password_hash
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# 🔐 App setup
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET")
if not app.secret_key:
    raise RuntimeError("❌ FLASK_SECRET is missing from environment variables. Set it in your .env file.")
app.permanent_session_lifetime = timedelta(minutes=30)

# 🔐 Rate limiting (CSRF removed)
limiter = Limiter(get_remote_address, app=app)

# 📁 Globals
LOG_FILE = "webhook_logs.json"
LOGS_USER = os.getenv("LOGS_USER")
LOGS_PASSWORD_HASH = os.getenv("LOGS_PASSWORD_HASH")

import stripe
app_env = os.getenv("APP_ENV", "local")
stripe.api_key = os.getenv("STRIPE_API_KEY_LIVE") if app_env == "production" else os.getenv("STRIPE_API_KEY_TEST")

# ✅ Utility Imports
from storage_utils import load_json, load_merge_map, save_merge_map
from cache_utils import load_cache, save_cache, get_cached_email
from log_utils import append_log_entry
from mailchimp_sync import sync_to_mailchimp
from config import MEMBERFUL_WEBHOOK_SECRET

# ✅ Custom login_required decorator
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ✅ Login/logout
@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    form = LoginForm()
    error = None

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        if username == LOGS_USER and check_password_hash(LOGS_PASSWORD_HASH, password):
            session["logged_in"] = True
            return redirect(url_for("admin_index"))
        else:
            error = "Invalid username or password"
            append_log_entry(
                event="login_failed",
                email=username or "unknown",
                status="failed",
                payload={
                    "ip": request.remote_addr,
                    "user_agent": request.headers.get("User-Agent"),
                    "error": error
                }
            )

    return render_template("login.html", form=form, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ✅ Jinja filter
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

# ✅ Signature verification
def verify_signature(request):
    signature = request.headers.get("X-Memberful-Webhook-Signature")
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

# ✅ Memberful Webhook
@app.route('/memberful-webhook', methods=['POST'])
def memberful_webhook():
    if not verify_signature(request):
        return abort(403, description="Invalid webhook signature")

    data = request.json
    event_type = data.get("event")
    print(f"Received webhook: {event_type}")
    print("Raw webhook payload:")
    print(data)

    # if event_type == "order.failed":
    #     # 🟡 Deprecated: 'order.failed' events are now handled via Stripe webhook
    #     member = data.get("order", {}).get("member") or {}
    #     if not member.get("email"):
    #         print("⚠️ No email in order.failed event")
    #         return '', 200
    #     sync_to_mailchimp(member, None, event_type)
    #     append_log_entry(event_type, member["email"], "success", payload=data)
    #     return '', 200

    member = data.get("member") or data.get("subscription", {}).get("member") or {}
    subscription = data.get("subscription") or {}

    if not member.get("email") and event_type != "member.deleted":
        print("⚠️ No email — skipping sync.")
        return '', 200

    if event_type in [
        "member_signup", "member_updated",
        "subscription.created", "subscription.updated",
        "subscription.renewed", "subscription.activated",
        "subscription.expired"
    ]:
        # 🆕 Add lead_stage for new subscriptions
        if event_type == "subscription.created":
            member["lead_stage"] = "Converted"

        sync_to_mailchimp(member, subscription, event_type)

        if event_type == "member_updated":
            member_id = member.get("id")
            current_email = member.get("email")
            cached_email = get_cached_email(member_id)
            changes = data.get("changed", {})
            if cached_email and cached_email != current_email:
                print(f"✳️ Email changed: {cached_email} → {current_email}")
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
        if member["email"]:
            subscription_stub = {
                "active": False,
                "plan_name": "",
                "autorenew": None,
                "expires_at": None
            }
            sync_to_mailchimp(member, subscription_stub, event_type)
            append_log_entry(event_type, member["email"], "success", payload=data)
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
                sync_to_mailchimp(member_stub, subscription_stub, event_type, override_guid=True)
                append_log_entry(event_type, cached_email, "success", payload=data)
                cache = load_cache()
                cache.pop(str(member_id), None)
                save_cache(cache)
            else:
                print(f"⚠️ No cached email for deleted member ID {member_id}")

    return '', 200

# ✅ GBX Webhook
@app.route('/gbx-member-profile-webhook', methods=['POST'])
def gbx_member_profile_webhook():
    try:
        payload = request.get_json(force=True)
        print("✅ Received GBX profile webhook payload:")
        print(json.dumps(payload, indent=2))

        if payload.get("secret") != os.getenv("GBX_WEBHOOK_SECRET"):
            print("❌ Invalid GBX webhook secret")
            return "Unauthorized", 403

        from gbx_sync import sync_gbx_profile_to_mailchimp
        sync_gbx_profile_to_mailchimp(payload)
        return '', 200
    except Exception as e:
        print(f"❌ Error processing GBX profile webhook: {e}")
        return 'Error', 500

# ✅ Stripe Webhook - For payment info
@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    # Pick correct secret based on environment
    app_env = os.getenv('APP_ENV', 'local')
    if app_env == 'production':
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET_PROD')
        stripe.api_key = os.getenv("STRIPE_API_KEY_PROD")
    else:
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET_LOCAL')
        stripe.api_key = os.getenv("STRIPE_API_KEY_TEST")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        print("❌ Invalid Stripe signature")
        return "Invalid signature", 400
    except Exception as e:
        print(f"❌ Error verifying webhook: {e}")
        return "Webhook error", 400

    event_type = event['type']
    print(f"⚡ Received Stripe event: {event_type}")

    # Supported tag-relevant events
    ADD_TAG_EVENTS = {
        'invoice.payment_failed',
        'charge.failed',
        'payment_intent.payment_failed'
    }

    REMOVE_TAG_EVENTS = {
        'invoice.payment_succeeded',
        'invoice.paid',
        'charge.succeeded',
        'payment_intent.succeeded'
    }

    if event_type in ADD_TAG_EVENTS.union(REMOVE_TAG_EVENTS):
        obj = event['data']['object']
        customer_id = obj.get('customer')

        if not customer_id:
            print("⚠️ No customer ID in event — skipping")
            return '', 200

        # 🔍 Check for member_id in metadata
        metadata = obj.get("metadata", {})
        if event_type.startswith("payment_intent.") and "charges" in obj:
            charges = obj.get("charges", {}).get("data", [])
            if charges and isinstance(charges, list):
                metadata = charges[0].get("metadata", {})

        if "member_id" not in metadata:
            print(f"⚠️ Skipping {event_type} — no member_id in metadata")
            return '', 200

        print(f"🔍 Fetching Stripe customer: {customer_id}")
        email = "unknown"  # Ensure it's defined for logging

        try:
            customer = stripe.Customer.retrieve(customer_id)
            email = customer.get("email")
            print(f"📧 Email from Stripe: {email}")

            if not email:
                print("⚠️ Stripe customer has no email — skipping Mailchimp sync")
                return '', 200

            # ✅ Safe name splitting
            customer_name = customer.get("name") or ""
            name_parts = customer_name.strip().split(" ", 1)
            first_name = name_parts[0] if len(name_parts) > 0 else ""
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            # Construct minimal member-like object
            member_stub = {
                "email": email,
                "id": "",
                "first_name": first_name,
                "last_name": last_name,
                "created_at": customer.get("created", "")
            }

            from mailchimp_sync import sync_to_mailchimp
            sync_to_mailchimp(member_stub, None, event_type, tag_only=True)

            from log_utils import append_log_entry
            append_log_entry(event_type, email, "success", payload=event)

        except Exception as e:
            print(f"❌ Failed to sync payment event to Mailchimp: {e}")
            from log_utils import append_log_entry
            append_log_entry(event_type, email, "error", diff={"error": str(e)}, payload=event)
            return "Error", 500

    else:
        print(f"ℹ️ Received unsupported event: {event_type} — no action taken")

    return '', 200

# ✅ Admin + API Routes
@app.route('/admin')
@login_required
def admin_index():
    return send_from_directory('admin-ui', 'index.html')

@app.route('/admin/<path:path>')
def admin_static(path):
    # allow public access to certain static assets
    if path in ['logo.png', 'logo-large.png', 'banana-bg.png', 'favicon.ico', 'favicon-16x16.png', 'favicon-32x32.png', 'apple-touch-icon.png']:
        return send_from_directory('admin-ui', path)

    # everything else still requires login
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    return send_from_directory('admin-ui', path)

@app.route('/webhook_logs.json')
@login_required
def serve_webhook_logs_json():
    try:
        return load_json(LOG_FILE), 200
    except Exception as e:
        print(f"❌ Error loading logs JSON: {e}")
        return {"error": "Could not load logs"}, 500

@app.route('/email_cache.json')
@login_required
def serve_email_cache():
    try:
        return load_cache(), 200
    except Exception as e:
        print(f"❌ Error loading email cache: {e}")
        return {"error": "Could not load email cache"}, 500

@app.route('/replay-log', methods=['POST'])
@login_required
def replay_log():
    try:
        data = request.get_json()
        print("📥 Incoming replay payload:", data)

        if not data or "event" not in data:
            print("⚠️ Missing event or invalid data:", request.data)
            return "Missing payload or event", 400

        print(f"🔁 Replaying event: {data['event']}")

        with app.test_request_context(
            '/memberful-webhook',
            method='POST',
            json=data,
            headers={"X-Memberful-Webhook-Signature": "REPLAY"}
        ):
            return memberful_webhook()

    except Exception as e:
        print("❌ Replay handler failed:", e)
        return "Server error", 500

@app.route('/api/merge-map', methods=['GET'])
@login_required
def get_merge_map():
    try:
        return jsonify(load_merge_map())
    except Exception as e:
        print(f"❌ Failed to load merge map: {e}")
        return jsonify({"error": "Failed to load merge map"}), 500

@app.route('/api/merge-map', methods=['POST'])
@login_required
def update_merge_map():
    try:
        data = request.get_json()
        save_merge_map(data)
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"❌ Failed to save merge map: {e}")
        return jsonify({"error": "Failed to save merge map"}), 500

@app.route('/health')
def health_check():
    return {"status": "ok"}, 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
