# tools/search_flights.py
import json
from datetime import datetime

from config import Config


def _date_only(value):
    return value.split("T")[0]  # tolerate "2026-07-08" and "2026-07-08T00:00:00"


def search_alternative_flights(origin, destination, travel_date):
    with (Config.MOCK_DATA_DIR / "alternatives.json").open(encoding="utf-8") as f:
        alternatives = json.load(f)

    target_date = _date_only(travel_date)
    matches = [
        option for option in alternatives
        if option["origin"].strip().upper() == origin.strip().upper()
        and option["destination"].strip().upper() == destination.strip().upper()
        and _date_only(option["date"]) == target_date
    ]
    return matches