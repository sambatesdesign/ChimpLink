# Environment Setup

This project uses a `.env` file to manage environment variables both locally and in production.

## 🔑 Required Variables

| Key                         | Description                              |
|----------------------------|------------------------------------------|
| `APP_ENV`                  | Set to `local` or `production`           |
| `MAILCHIMP_API_KEY`        | Your Mailchimp API key                   |
| `MAILCHIMP_LIST_ID`        | Your Mailchimp audience/list ID          |
| `MAILCHIMP_SERVER_PREFIX`  | Mailchimp server prefix (e.g., `us10`)   |
| `MEMBERFUL_WEBHOOK_SECRET`| Secret used to verify incoming webhooks  |
| `LOGS_USER`                | Username for log page basic auth         |
| `LOGS_PASSWORD_HASH`       | Hashed password for log auth             |
| `DIGITALOCEAN_SPACE_KEY`   | Spaces API Key ID (prod only)            |
| `DIGITALOCEAN_SPACE_SECRET`| Spaces API Secret (prod only)            |
| `DIGITALOCEAN_SPACE_REGION`| e.g., `nyc3`                             |
| `DIGITALOCEAN_SPACE_BUCKET`| e.g., `keepabl-com`                      |
| `DIGITALOCEAN_SPACE_FOLDER`| e.g., `webhook_logs`                     |

## 🧪 Local Development

Set `APP_ENV=local` and all variables in a `.env` file at the root of the project. Use `python-dotenv` to load them automatically.

