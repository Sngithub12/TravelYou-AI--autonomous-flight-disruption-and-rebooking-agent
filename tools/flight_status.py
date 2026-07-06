import json

from config import Config


def get_flight_status(flight_number):
    with (Config.MOCK_DATA_DIR / "flight_status.json").open(encoding="utf-8") as status_file:
        statuses = json.load(status_file)
    return statuses.get(flight_number, {"status": "unknown", "delay_minutes": 0})
