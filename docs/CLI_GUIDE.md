# CLI Test Utility Guide

You can simulate real Memberful webhook events using our CLI test utility.

## 🚀 How to Run Locally

```bash
python test_workflow_verified_step.py
```

This script will:

- Simulate signup, subscription, order failure, email change, etc.
- Validate Mailchimp merge fields
- Verify contact tagging
- Check email change syncs
- Clean up the contact at the end

No input prompts are needed — it's fully automated.

## 🔁 Use `.env` for URL Override

By default, it posts to `http://localhost:5050`. If using ngrok, update the `WEBHOOK_URL` value in the script or via `.env`.
