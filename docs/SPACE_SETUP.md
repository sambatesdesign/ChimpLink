# DigitalOcean Spaces Setup

We use DigitalOcean Spaces to persist:

- `webhook_logs.json`
- `member_email_cache.json`

## ✅ Environment Variables

Add the following to your `.env` or DO App Environment:

```
APP_ENV=production
DIGITALOCEAN_SPACE_KEY=...
DIGITALOCEAN_SPACE_SECRET=...
DIGITALOCEAN_SPACE_REGION=nyc3
DIGITALOCEAN_SPACE_BUCKET=keepabl-com
DIGITALOCEAN_SPACE_FOLDER=webhook_logs
```

## 📤 Uploading Initial Files

Use this Python snippet to upload your current local files:

```python
import boto3

client = boto3.client(
    "s3",
    region_name="nyc3",
    endpoint_url="https://nyc3.digitaloceanspaces.com",
    aws_access_key_id="your_key",
    aws_secret_access_key="your_secret"
)

client.upload_file("webhook_logs.json", "keepabl-com", "webhook_logs/webhook_logs.json")
client.upload_file("member_email_cache.json", "keepabl-com", "webhook_logs/member_email_cache.json")
```
