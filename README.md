
# 📬 Memberful → Mailchimp Sync Webhook App

This is a secure Flask-based webhook handler that listens for Memberful events and syncs data to your Mailchimp audience. It handles events like signups, subscription changes, email changes, payment failures, and more—keeping your list accurate and actionable with persistent logging, CLI test simulation, and Digital Ocean storage support.

---

## 🧠 What It Does

- 🔐 Securely receives Memberful webhooks with HMAC signature validation
- 🔄 Syncs Mailchimp subscriber `merge_fields` based on subscription info
- 🏷️ Adds or removes Mailchimp tags like **"Payment Failed"** based on order status
- ✉️ Detects email address changes and avoids duplicate Mailchimp entries
- 🧠 Uses a local + remote cache to track Memberful ID ↔ Email for safe deletion and replay
- 📋 Maintains a persistent event log (now backed by DigitalOcean Spaces)
- 📈 `/logs` admin page with search, filter, and **event replay** features
- 🔧 Fully testable via CLI with simulated webhook events

---

## 🗂️ Project File Structure

| File / Folder              | Purpose |
|---------------------------|---------|
| `app.py`                  | Main Flask app with all route and webhook logic |
| `mailchimp_sync.py`       | Handles syncing data to Mailchimp |
| `cache_utils.py`          | Email caching logic with fallback to Spaces |
| `log_utils.py`            | Append + persist event logs (local or DigitalOcean Spaces) |
| `storage_utils.py`        | Abstract file I/O to local or DigitalOcean Spaces |
| `test_workflow_verified_step.py` | CLI tester for webhook simulation (automated) |
| `templates/logs.html`     | Web UI for viewing and replaying webhook events |
| `config.py`               | Loads env vars (via `.env`) for keys and secret configuration |
| `.env`                    | Stores API keys, webhook secret, and admin credentials (never committed!) |

---

## 📋 Webhook Events Handled

| Event                      | Description |
|---------------------------|-------------|
| `member_signup`           | New member registered |
| `member_updated`          | Member details changed (e.g., email address) |
| `member.deleted`          | Member deleted from Memberful |
| `subscription.created`    | Subscription started |
| `subscription.updated`    | Plan upgraded or downgraded |
| `subscription.activated`  | Subscription manually activated |
| `subscription.renewed`    | Subscription auto-renewed |
| `subscription.expired`    | Subscription billing period ended |
| `subscription.deactivated`| Subscription canceled |
| `subscription.deleted`    | Subscription deleted |
| `order.failed`            | Billing failed — triggers `"Payment Failed"` tag in Mailchimp |

---

# 🚀 Deployment + Setup Instructions

## ✅ 1. Clone and Setup

```bash
git clone https://github.com/your-org/your-repo.git
cd your-repo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## ✅ 2. Configure `.env` File

Create a file called `.env` and add:

```env
APP_ENV=local

# Mailchimp
MAILCHIMP_API_KEY=your-mailchimp-key
MAILCHIMP_LIST_ID=your-list-id
MAILCHIMP_SERVER_PREFIX=usX

# Memberful
MEMBERFUL_WEBHOOK_SECRET=your-secret

# Logs page login
LOGS_USER=admin
LOGS_PASSWORD_HASH=pbkdf2:sha256:...

# Optional (for production)
DIGITALOCEAN_SPACE_KEY=...
DIGITALOCEAN_SPACE_SECRET=...
DIGITALOCEAN_SPACE_REGION=nyc3
DIGITALOCEAN_SPACE_BUCKET=your-bucket
DIGITALOCEAN_SPACE_FOLDER=webhook_logs
```

> To generate a secure `LOGS_PASSWORD_HASH`:
```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('YourPasswordHere'))"
```

---

## ✅ 3. Start the Server (Dev)

```bash
python app.py
```

Runs locally at:
```
http://localhost:5050
```

Use [Ngrok](https://ngrok.com/) to test webhooks:

```bash
ngrok http 5050
```

---

## ✅ 4. Run CLI Tests

The CLI test simulates a full webhook flow (signup → subscription → failure → recovery → email change):

```bash
python test_workflow_verified_step.py
```

---

### 🛠️ Admin Panel

The ChimpLink Admin Panel provides a lightweight browser interface for monitoring and managing webhook activity between Memberful and Mailchimp.

#### 📍 Location

Accessible at:  
`http://localhost:5050/admin` (or your deployed domain)

#### 🚀 Features

- **Dashboard Tab**  
  Visual overview of recent webhook activity:
  - Total webhooks received
  - Success vs failure counts
  - Top 5 event types
  - Bar chart of event types
  - Line chart of webhook frequency over time

- **Logs Tab**  
  Detailed view of every webhook event:
  - Date, time, event type, target email, and status
  - View payload and diffs
  - One-click replay support for any webhook

- **Email Cache Tab**  
  Browse the local cache of `Memberful ID → email` mappings used for syncing deleted or changed records.

#### 🧪 Developer Notes

- Frontend built with **Tailwind CSS** (via CDN)
- Charts powered by **Chart.js**
- Interactive tabs, logs, and charts loaded dynamically via `main.js`
- Admin panel lives in the `admin-ui/` folder and is served statically via Flask


## ✅ 6. Health Check

Use `/health` for uptime robot monitoring:

```json
{ "status": "ok" }
```

---

## ✅ 7. Persistent Storage with DigitalOcean Spaces

By default:
- Logs and cache are local in development
- In production, files read/write from Spaces automatically

Ensure `APP_ENV=production` and DigitalOcean credentials are present in your environment.

> **Important:** Logs and cache files will not be overwritten on redeploy. They are stored in your configured bucket folder.

---

## 🧪 Testing Tips

- Backfill your `member_email_cache.json` if launching with existing users
- Test using realistic email addresses like `mazespacedev123@gmail.com`
- Set up CLI test flows before pushing production changes

---

## ❤️ Built With

- Python 3
- Flask
- Mailchimp Marketing API
- Memberful Webhooks
- DigitalOcean Spaces
- Boto3 + Gunicorn + Flask-HTTPAuth

MIT License
