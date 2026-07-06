"""
Mock data generator for TripMind AI.

Combines real reference data with synthetic passenger details to produce a
richer, more realistic mock dataset than hand-typed JSON — while keeping
everything fully offline and static, so the demo has zero runtime dependency
on external services.

Sources:
- OpenFlights (github.com/jpatokal/openflights) — real airport codes/names
  and real airline names/IATA codes. Free, static, no API key.
- Faker — synthetic passenger names, kept clearly fictional (no real people).
- Hand-coded realistic delay-reason categories, modeled on the categories
  the US DOT uses for flight delay causes (carrier, weather, NAS, late
  aircraft, security) — not pulled live, just realistic wording.

Usage:
    python3 generate_mock_data.py
Writes: mock_data/bookings.json, mock_data/flight_status.json,
        mock_data/alternatives.json
"""
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

random.seed(42)  # reproducible output — rerun without the seed for fresh variety
fake = Faker()
Faker.seed(42)

MOCK_DATA_DIR = Path(__file__).resolve().parent / "mock_data"

NUM_BOOKINGS = 10
ALT_FLIGHTS_PER_ROUTE = 3  # 10 routes x 3 = 30 alternative flights

DELAY_REASONS = [
    ("carrier", "Aircraft maintenance issue discovered during pre-flight check."),
    ("weather", "Severe weather system affecting the departure corridor."),
    ("nas", "Air traffic control ground delay due to airspace congestion."),
    ("late_aircraft", "Late arrival of the inbound aircraft from a prior leg."),
    ("security", "Extended security screening delay at the departure gate."),
]

LOYALTY_TIERS = ["Silver", "Gold", "Platinum"]
SEAT_PREFS = ["aisle", "window", "middle"]

# A curated shortlist of major real airports (IATA, name, city) — filtered
# from the full OpenFlights set to ones likely to have real onward routes.
PREFERRED_IATA = [
    "JFK", "LHR", "ORD", "NRT", "DXB", "CDG", "SFO", "SYD",
    "SIN", "FRA", "AMS", "HKG", "LAX", "MIA", "SEA", "YYZ",
]


def load_airports():
    airports = {}
    with open(MOCK_DATA_DIR.parent / "openflights_airports.dat", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 5:
                continue
            iata = row[4].strip('"')
            name = row[1].strip('"')
            city = row[2].strip('"')
            if iata in PREFERRED_IATA:
                airports[iata] = {"name": name, "city": city}
    return airports


def load_airlines():
    airlines = []
    with open(MOCK_DATA_DIR.parent / "openflights_airlines.dat", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 8:
                continue
            name = row[1].strip('"')
            iata = row[3].strip('"')
            active = row[7].strip('"') if len(row) > 7 else "N"
            # Filter to plausible, currently-active, named passenger carriers
            if (
                active == "Y"
                and len(iata) == 2
                and iata.isalnum()
                and name
                and "Unknown" not in name
                and not name.startswith("[")
            ):
                airlines.append({"name": name, "iata": iata})
    return airlines


def pick_route(airport_codes, used_routes):
    while True:
        origin, destination = random.sample(airport_codes, 2)
        if (origin, destination) not in used_routes:
            used_routes.add((origin, destination))
            return origin, destination


def make_flight_number(airline_iata):
    return f"{airline_iata}-{random.randint(100, 999)}"


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def generate():
    airports = load_airports()
    airlines = load_airlines()
    airport_codes = list(airports.keys())

    bookings = {}
    flight_status = {}
    alternatives = []
    used_routes = set()

    base_date = datetime(2026, 7, 8)

    for i in range(NUM_BOOKINGS):
        origin, destination = pick_route(airport_codes, used_routes)
        primary_airline = random.choice(airlines)
        flight_number = make_flight_number(primary_airline["iata"])

        dep_hour = random.randint(6, 22)
        departure_time = base_date.replace(hour=dep_hour, minute=random.choice([0, 15, 30, 45]))
        flight_duration_hours = random.randint(2, 14)
        arrival_time = departure_time + timedelta(hours=flight_duration_hours, minutes=random.choice([0, 20, 40]))

        # ~30% of passengers have no onward connection at all — a real edge
        # case your planner.py needs to handle (some bookings are one-leg trips).
        has_connection = random.random() > 0.3
        booking = {
            "booking_id": f"TM-{random.randint(10000, 99999)}",
            "flight_number": flight_number,
            "origin": origin,
            "destination": destination,
            "date": base_date.strftime("%Y-%m-%d"),
            "departure_time": iso(departure_time),
            "arrival_time": iso(arrival_time),
            "passenger": {
                "name": fake.name(),
                "loyalty_tier": random.choice(LOYALTY_TIERS),
                "preferred_airline": primary_airline["name"],
                "seat_preference": random.choice(SEAT_PREFS),
                "latest_acceptable_arrival": iso(arrival_time + timedelta(hours=random.randint(6, 30))),
            },
        }
        if has_connection:
            buffer_minutes = random.choice([45, 60, 75, 90, 150, 240])  # mix of tight and generous
            booking["connection_departure"] = iso(arrival_time + timedelta(minutes=buffer_minutes))
            booking["minimum_connection_minutes"] = random.choice([45, 60, 75])

        bookings[booking["booking_id"]] = booking

        flight_status[flight_number] = {
            "status": "on_time",
            "delay_minutes": 0,
            "last_updated": iso(departure_time - timedelta(hours=4)),
        }

        # Generate real-feeling alternative flights for this route
        route_alternatives = []
        used_alt_airlines = {primary_airline["iata"]}
        for _ in range(ALT_FLIGHTS_PER_ROUTE):
            alt_airline = random.choice(airlines)
            attempts = 0
            while alt_airline["iata"] in used_alt_airlines and attempts < 10:
                alt_airline = random.choice(airlines)
                attempts += 1
            used_alt_airlines.add(alt_airline["iata"])

            alt_dep = departure_time + timedelta(hours=random.randint(1, 5), minutes=random.choice([0, 15, 30]))
            alt_duration = flight_duration_hours + random.choice([0, 0, 1, 2])  # occasional longer routing
            alt_arrival = alt_dep + timedelta(hours=alt_duration, minutes=random.choice([0, 25, 50]))
            stops = 0 if random.random() > 0.25 else 1

            route_alternatives.append({
                "flight_number": make_flight_number(alt_airline["iata"]),
                "airline": alt_airline["name"],
                "origin": origin,
                "destination": destination,
                "date": base_date.strftime("%Y-%m-%d"),
                "departure_time": iso(alt_dep),
                "arrival_time": iso(alt_arrival),
                "stops": stops,
                "seat_available": random.choice(SEAT_PREFS),
                "price_delta": random.choice([0, 20, 40, 60, 80, 100, 120, 150]),
            })
        alternatives.extend(route_alternatives)

    MOCK_DATA_DIR.mkdir(exist_ok=True)
    with (MOCK_DATA_DIR / "bookings.json").open("w", encoding="utf-8") as f:
        json.dump(bookings, f, indent=2)
    with (MOCK_DATA_DIR / "flight_status.json").open("w", encoding="utf-8") as f:
        json.dump(flight_status, f, indent=2)
    with (MOCK_DATA_DIR / "alternatives.json").open("w", encoding="utf-8") as f:
        json.dump(alternatives, f, indent=2)

    print(f"Generated {len(bookings)} bookings, {len(alternatives)} alternative flights.")
    print(f"Airports used: {sorted(set(b['origin'] for b in bookings.values()) | set(b['destination'] for b in bookings.values()))}")
    print("Sample booking IDs:", list(bookings.keys()))


if __name__ == "__main__":
    generate()
