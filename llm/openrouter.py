import time

import requests

from config import Config
from tools.logger import log_event


def _call_openrouter(payload, timeout=15, retries=2):
    """Shared low-level caller with retries, backoff, and consistent error logging.
    Works against OpenRouter or any OpenAI-compatible endpoint (e.g. Ollama) —
    swap Config.OPENROUTER_BASE_URL in .env to point elsewhere."""
    headers = {"Content-Type": "application/json"}
    if Config.OPENROUTER_API_KEY:
        headers["Authorization"] = f"Bearer {Config.OPENROUTER_API_KEY}"

    last_error = None
    for attempt in range(retries + 1):
        try:
            response = requests.post(
                Config.OPENROUTER_BASE_URL,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            if "choices" not in data or not data["choices"]:
                raise ValueError(f"Unexpected response shape: {data}")
            return data
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            log_event("LLM call failed", {"attempt": attempt + 1, "error": str(exc)})
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))  # simple backoff
    log_event("LLM call exhausted retries", {"error": str(last_error)})
    return None


def generate_notification_with_llm(booking, status, impact, selected):
    prompt = (
        "Write a concise, reassuring airline disruption notification. "
        f"Passenger: {booking['passenger']['name']}. "
        f"Original flight: {booking['flight_number']} {status['status']}. "
        f"Impact: {impact['reason']}. "
        f"New flight: {selected['flight_number']} on {selected['airline']}, "
        f"departing {selected['departure_time']}, arriving {selected['arrival_time']}."
    )
    data = _call_openrouter({
        "model": Config.OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    })
    if data is None:
        # Graceful degradation: never let a demo die on a flaky LLM call.
        return (
            f"Hi {booking['passenger']['name']}, your flight "
            f"{booking['flight_number']} was {status['status']}. "
            f"We've moved you to {selected['flight_number']} on {selected['airline']}."
        )
    return data["choices"][0]["message"]["content"].strip()


def generate_text_with_llm(prompt, temperature=0.4, fallback=None, timeout=40):
    """Plain completion, no tools — used for reasoning narration in the
    hybrid orchestrator, where the tool sequence is fixed in Python but the
    LLM still explains/justifies each step in its own words. Default timeout
    raised from 15s to 40s — local Ollama CPU inference is slower and more
    variable than a hosted API, and a premature timeout just wastes a retry
    round-trip for no benefit."""
    data = _call_openrouter({
        "model": Config.OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }, timeout=timeout)
    if data is None:
        return fallback if fallback is not None else "(reasoning unavailable)"
    return data["choices"][0]["message"]["content"].strip()


def call_agent_step(messages, tools, tool_choice="auto"):
    """Single agentic step: LLM decides whether to call a tool or respond directly.
    Returns the raw message dict from the API (may contain tool_calls), or None
    if the call failed after retries."""
    data = _call_openrouter({
        "model": Config.OPENROUTER_MODEL,
        "messages": messages,
        "tools": tools,
        "tool_choice": tool_choice,
        "temperature": 0.2,
    }, timeout=30)
    if data is None:
        return None
    return data["choices"][0]["message"]
