from datetime import datetime, timezone

from config import Config


def log_event(message, payload=None):
    Config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    suffix = f" | {payload}" if payload is not None else ""
    line = f"{timestamp} | {message}{suffix}"
    print(line)  # visible in terminal during the recording
    with Config.LOG_FILE.open("a", encoding="utf-8") as log_file:
        log_file.write(line + "\n")