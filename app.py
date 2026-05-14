"""
Slack Kudos Bot application entrypoint.
"""

import os
import random
from typing import List

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from slack_bolt import App as BoltApp
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt.adapter.socket_mode import SocketModeHandler

from summarizer import summarize_thread

load_dotenv()

bolt_app = BoltApp(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)
slack_handler = SlackRequestHandler(bolt_app)

app = Flask(__name__)

KUDOS_CHANNEL_ID = os.environ.get("KUDOS_CHANNEL_ID")

CELEBRATION_EMOJIS = ["🎉", "🙌", "⭐", "🚀", "💪", "🔥", "✨", "👏", "💯", "🏆"]

# Funny fail-safe messages (randomly picked)
SELF_KUDOS_MESSAGES = [
    "Nice try, but you can't kudos yourself! Don't be a narc lol 😏",
    "Self-love is important, but this ain't the way chief 💅",
    "Plot twist: You can't be your own hype man here 📢",
    "Error 403: Self-appreciation forbidden. Try a mirror instead 🪞",
    "Whoa there, Kanye. Maybe let someone else give you props 🎤",
    "Main character energy is great, but kudos need a supporting cast 🎬",
    "Task failed successfully: Self-kudos blocked ❌",
    "The audacity! The confidence! ...but still no. 😂",
    "Sir/Ma'am, this is a peer recognition system 🫠",
    "I admire the self-confidence, but that's not how this works 😅",
]

BOT_KUDOS_MESSAGES = [
    "I guide others to a treasure I cannot possess. 🔴💀",
    "Beep boop... I appreciate the thought, but I'm just code 🤖💔",
    "I'm flattered, but my love language is uptime, not kudos ⚡",
    "Thanks, but I literally can't feel joy. I'm a bot. 🫥",
    "Error: Cannot process emotions. Redirecting kudos to /dev/null 🕳️",
    "That's sweet, but I run on API calls, not compliments 🔌",
    "*blushes in binary* ...but seriously, kudos a human instead 01100001",
    "I'm just here to serve. Like a vending machine, but for recognition 🎰",
]


def fetch_thread_messages(client, channel_id: str, thread_ts: str) -> List[str]:
    """Fetch all messages from a thread."""
    try:
        # First try to join the channel (in case bot was just added)
        try:
            client.conversations_join(channel=channel_id)
        except Exception:
            pass  # Already in channel or can't join (private)
        
        result = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=50,
        )
        messages_list = []
        for msg in result.get("messages", []):
            if msg.get("text") and not msg.get("bot_id"):
                messages_list.append(msg["text"])
        print(f"Fetched {len(messages_list)} messages from thread")
        return messages_list
    except Exception as e:
        print(f"Error fetching thread (channel={channel_id}, ts={thread_ts}): {e}")
        return []


def get_thread_link(client, channel_id: str, thread_ts: str) -> str:
    """Generate a permalink to the thread."""
    try:
        result = client.chat_getPermalink(channel=channel_id, message_ts=thread_ts)
        return result.get("permalink", "")
    except Exception as e:
        print(f"Error getting permalink: {e}")
        return ""


def post_kudos_to_channel(client, sender_id: str, receiver_id: str, summary: str, thread_link: str):
    """Post the kudos message to the #kudos channel."""
    if not KUDOS_CHANNEL_ID:
        print("KUDOS_CHANNEL_ID not set")
        return False

    try:
        emoji = random.choice(CELEBRATION_EMOJIS)
        # Use Slack's link format: <URL|text> for hyperlinked summary
        if thread_link:
            summary_with_link = f"<{thread_link}|{summary}>"
        else:
            summary_with_link = summary
        message = f"<@{sender_id}> gave <@{receiver_id}> a kudos for {summary_with_link} {emoji}"
        client.chat_postMessage(
            channel=KUDOS_CHANNEL_ID,
            text=message,
            unfurl_links=False,
            unfurl_media=False,
        )
        return True
    except Exception as e:
        print(f"Error posting to kudos channel: {e}")
        return False


# ============================================================
# MESSAGE SHORTCUT: Three-dot menu -> "Give Kudos"
# ============================================================

@bolt_app.shortcut("give_kudos")
def handle_give_kudos_shortcut(ack, shortcut, client):
    """
    Handle the 'Give Kudos' message shortcut.
    Opens a modal to select who gets the kudos.
    """
    ack()

    message = shortcut.get("message", {})
    channel_id = shortcut.get("channel", {}).get("id")
    message_ts = message.get("ts")
    thread_ts = message.get("thread_ts") or message_ts
    message_user = message.get("user")  # Author of the clicked message

    # Store context in private_metadata
    metadata = f"{channel_id}|{thread_ts}"

    client.views_open(
        trigger_id=shortcut["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "kudos_modal",
            "private_metadata": metadata,
            "title": {"type": "plain_text", "text": "Give Kudos"},
            "submit": {"type": "plain_text", "text": "Send Kudos"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "recipient_block",
                    "element": {
                        "type": "users_select",
                        "action_id": "recipient",
                        "initial_user": message_user,
                        "placeholder": {"type": "plain_text", "text": "Select a person"},
                    },
                    "label": {"type": "plain_text", "text": "Who deserves kudos?"},
                },
                {
                    "type": "input",
                    "block_id": "custom_message_block",
                    "optional": True,
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "custom_message",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "e.g., helping debug the login issue",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Custom message (optional)"},
                    "hint": {
                        "type": "plain_text",
                        "text": "Leave empty to auto-summarize the thread. Use this for work done outside Slack or to write your own message.",
                    },
                },
            ],
        },
    )


def get_bot_user_id(client) -> str:
    """Get the bot's own user ID."""
    try:
        result = client.auth_test()
        return result.get("user_id", "")
    except Exception as e:
        print(f"Error getting bot user ID: {e}")
        return ""


def send_ephemeral_message(client, channel_id: str, user_id: str, message: str):
    """Send an ephemeral message only visible to the user."""
    try:
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=message,
        )
    except Exception as e:
        print(f"Error sending ephemeral message: {e}")


@bolt_app.view("kudos_modal")
def handle_kudos_modal_submission(ack, body, client, view):
    """Handle the kudos modal submission."""
    ack()

    sender_id = body["user"]["id"]
    receiver_id = view["state"]["values"]["recipient_block"]["recipient"]["selected_user"]

    # Get custom message if provided
    custom_message_data = view["state"]["values"]["custom_message_block"]["custom_message"]
    custom_message_value = custom_message_data.get("value") if custom_message_data else None
    custom_message = custom_message_value.strip() if custom_message_value else ""

    # Parse metadata
    metadata = view.get("private_metadata", "")
    parts = metadata.split("|")
    channel_id = parts[0] if len(parts) > 0 else None
    thread_ts = parts[1] if len(parts) > 1 else None

    # Funny fail-safe: Prevent self-kudos
    if receiver_id == sender_id:
        if channel_id:
            send_ephemeral_message(client, channel_id, sender_id, random.choice(SELF_KUDOS_MESSAGES))
        return

    # Funny fail-safe: Prevent kudos to the bot itself
    bot_user_id = get_bot_user_id(client)
    if receiver_id == bot_user_id:
        if channel_id:
            send_ephemeral_message(client, channel_id, sender_id, random.choice(BOT_KUDOS_MESSAGES))
        return

    # Use custom message if provided, otherwise auto-summarize
    if custom_message:
        summary = custom_message
        # Still get thread link for context
        thread_link = get_thread_link(client, channel_id, thread_ts) if thread_ts and channel_id else ""
    elif thread_ts and channel_id:
        thread_messages = fetch_thread_messages(client, channel_id, thread_ts)
        summary = summarize_thread(thread_messages)
        thread_link = get_thread_link(client, channel_id, thread_ts)
    else:
        summary = "their contributions"
        thread_link = ""

    # Post to #kudos channel
    post_kudos_to_channel(client, sender_id, receiver_id, summary, thread_link)


@app.get("/")
def healthcheck():
    """Simple health endpoint for local and hosted checks."""
    return jsonify({"ok": True, "service": "slack-kudos"})


@app.route("/slack/events", methods=["GET", "POST"])
def slack_events():
    """Handle Slack interactions over HTTP."""
    return slack_handler.handle(request)


def main():
    """Start the bot locally."""
    app_token = os.environ.get("SLACK_APP_TOKEN")

    if app_token:
        print("Starting bot in Socket Mode...")
        handler = SocketModeHandler(bolt_app, app_token)
        handler.start()
    else:
        port = int(os.environ.get("PORT", 3000))
        print(f"Starting bot in HTTP mode on port {port}...")
        app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
