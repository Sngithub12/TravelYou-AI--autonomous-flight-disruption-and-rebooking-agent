import json

from config import Config
from tools.logger import log_event


def _load_bookings():
    try:
        with (Config.MOCK_DATA_DIR / "bookings.json").open(encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        log_event("Failed to load bookings.json", {"error": str(exc)})
        raise


def get_booking(booking_id=None):
    bookings = _load_bookings()
    if not bookings:
        raise ValueError("bookings.json is empty — run generate_mock_data.py first.")

    if booking_id and booking_id in bookings:
        return bookings[booking_id]
    if booking_id:
        log_event("Unknown booking_id, falling back to first available", {"requested": booking_id})

    # No specific booking requested (or it didn't exist) — use the first one
    # in the file rather than a hardcoded ID, since generate_mock_data.py
    # produces fresh random IDs on every run.
    return next(iter(bookings.values()))


def list_bookings():
    """Returns all bookings — useful for a picker UI if you add one later."""
    return list(_load_bookings().values())
