"""
OpenAI-powered thread summarization for kudos context.
"""

import os
import re
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = None


def get_client():
    """Lazily initialize OpenAI client."""
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        _client = OpenAI(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You summarize Slack thread conversations into a brief phrase describing the task or achievement.
Rules:
- Maximum 10 words
- Focus on WHAT was done (e.g., "fixing the dashboard bug", "deploying the new API", "reviewing the PR")
- Start with a verb in -ing form (fixing, implementing, reviewing, merging, etc.)
- Do NOT include names, @mentions, or pronouns
- Do NOT use generic phrases like "their work" or "contributions"
- Be specific about the actual task discussed
- Return ONLY the summary phrase, nothing else"""


def summarize_thread(messages: List[str]) -> str:
    """
    Summarize a list of thread messages into a brief description.

    Args:
        messages: List of message texts from the thread

    Returns:
        A brief summary string (~10 words max)
    """
    thread_text = build_model_input(messages)
    if not thread_text:
        return safe_fallback_summary()

    try:
        response = get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Summarize this thread:\n\n{thread_text}"},
            ],
            max_tokens=50,
            temperature=0.3,
        )
        summary = response.choices[0].message.content.strip()

        # Remove quotes if the model wrapped the response
        if summary.startswith('"') and summary.endswith('"'):
            summary = summary[1:-1]

        return summary or safe_fallback_summary()

    except Exception as e:
        print(f"OpenAI summarization failed: {e}")
        return safe_fallback_summary()


def build_model_input(messages: List[str]) -> str:
    """Prepare a minimally redacted thread transcript for summarization."""
    sanitized_messages = [sanitize_message(message) for message in messages]
    sanitized_messages = [message for message in sanitized_messages if message]
    if not sanitized_messages:
        return ""

    thread_text = "\n".join(sanitized_messages)
    if len(thread_text) > 2000:
        thread_text = thread_text[:2000] + "..."
    return thread_text


def sanitize_message(message: str) -> str:
    """Strip Slack-specific identifiers and obvious direct identifiers."""
    text = message.strip()
    if not text:
        return ""

    substitutions = [
        (r"<@[^>]+>", "@someone"),
        (r"<#[^>]+>", "#channel"),
        (r"<(?:mailto:)?([^>|]+)\|([^>]+)>", r"\2"),
        (r"<https?://[^>|]+(?:\|([^>]+))?>", r"\1"),
        (r"\b[A-Z0-9]{9,}\b", "[id]"),
        (r"\b[\w\.-]+@[\w\.-]+\.\w+\b", "[email]"),
    ]
    for pattern, replacement in substitutions:
        text = re.sub(pattern, replacement, text)

    text = re.sub(r"https?://\S+", "[link]", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_fallback_summary() -> str:
    """Return a non-sensitive fallback when summarization is unavailable."""
    return "helping with the thread"
