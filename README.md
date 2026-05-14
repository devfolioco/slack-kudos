# Slack Kudos Bot (v1.0)
Made for Devfolio

A lightweight Slack bot for turning a message shortcut into a public kudos post.

## What It Does

- Adds a **message shortcut** called `Give Kudos`
- Opens a modal so the sender can choose the recipient
- Either summarizes the thread with OpenAI or uses a custom message
- Posts a compact celebration message in a shared kudos channel

This repo does **not** currently persist kudos history or expose a slash command flow.

## Privacy Notes

- Thread text is never written to application logs
- Slack mentions, IDs, emails, and links are sanitized before being sent to OpenAI
- If summarization fails, the bot falls back to a generic safe summary instead of echoing Slack text

## Slack App Setup

### 1. Create the Slack app

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Create a new app from scratch
3. Install it into your workspace

### 2. Add bot scopes

Add these bot token scopes under **OAuth & Permissions**:

| Scope | Purpose |
|-------|---------|
| `chat:write` | Post the kudos message |
| `channels:history` | Read public thread context |
| `groups:history` | Read private channel thread context |
| `users:read` | Resolve bot identity for self-protection checks |

### 3. Enable Interactivity

Under **Interactivity & Shortcuts**:

1. Turn interactivity on
2. Set the request URL to `https://your-domain/slack/events`

### 4. Create the message shortcut

Under **Interactivity & Shortcuts**, create a **Message Shortcut**:

- **Name:** `Give Kudos`
- **Short description:** `Celebrate someone for this thread`
- **Callback ID:** `give_kudos`

### 5. Optional local Socket Mode

For local development, you can enable **Socket Mode** and create an app-level token with the `connections:write` scope. Set that token as `SLACK_APP_TOKEN`.

## Environment Variables

Copy `.env.example` to `.env` for local development.

| Variable | Required | Purpose |
|----------|----------|---------|
| `SLACK_BOT_TOKEN` | Yes | Slack bot token |
| `SLACK_SIGNING_SECRET` | Yes | Verifies Slack requests in HTTP mode |
| `KUDOS_CHANNEL_ID` | Yes | Channel that receives kudos posts |
| `SLACK_BOT_USER_ID` | Optional | Bot's own user ID (`Uxxx`); enables the "can't kudos the bot" fail-safe |
| `OPENROUTER_API_KEY` | Optional | Enables AI-generated thread summaries via OpenRouter |
| `SLACK_APP_TOKEN` | Optional | Enables local Socket Mode |

## Running Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

- If `SLACK_APP_TOKEN` is set, the bot runs in Socket Mode
- Otherwise it runs a local Flask server on `http://localhost:3000`

## Deploying

### Vercel

This repo exports a Flask app from `app.py`, which makes it compatible with Vercel's Python runtime.

1. Import the repo into Vercel
2. Set the environment variables above
3. Deploy
4. Point Slack interactivity to `https://your-project.vercel.app/slack/events`

### Railway or other always-on hosts

The bot also works on Railway or similar Python hosts. In HTTP mode, the `Procfile` starts the Flask app with:

```bash
web: python app.py
```

## Architecture

```text
app.py         Flask + Slack Bolt app, shortcut handlers, local entrypoint
summarizer.py  Sanitized OpenAI thread summarization
```

## License

MIT
