from datetime import datetime


def score_alternative(option, passenger):
    arrival = datetime.fromisoformat(option["arrival_time"])
    departure = datetime.fromisoformat(option["departure_time"])
    duration_minutes = int((arrival - departure).total_seconds() / 60)

    score = 100
    factors = [{"label": "Base itinerary quality", "value": 100}]

    duration_penalty = round(duration_minutes * -0.06, 2)
    stop_penalty = option["stops"] * -12
    fare_penalty = round(option["price_delta"] * -0.03, 2)

    score += duration_penalty
    score += stop_penalty
    score += fare_penalty
    factors.extend(
        [
            {"label": f"{duration_minutes} minute total travel time", "value": duration_penalty},
            {"label": f"{option['stops']} stop penalty", "value": stop_penalty},
            {"label": f"${option['price_delta']} fare delta", "value": fare_penalty},
        ]
    )

    if option["airline"] == passenger["preferred_airline"]:
        score += 14
        factors.append({"label": "Preferred airline match", "value": 14})
    if option["seat_available"] == passenger["seat_preference"]:
        score += 5
        factors.append({"label": "Seat preference available", "value": 5})
    if option["arrival_time"] <= passenger["latest_acceptable_arrival"]:
        score += 10
        factors.append({"label": "Arrives before passenger deadline", "value": 10})
    else:
        score -= 25
        factors.append({"label": "Misses passenger arrival deadline", "value": -25})

    return {
        "score": round(score, 2),
        "factors": factors,
    }


def choose_best_itinerary(alternatives, passenger):
    ranked = []
    for option in alternatives:
        scorecard = score_alternative(option, passenger)
        scored = dict(option)
        scored["score"] = scorecard["score"]
        scored["score_factors"] = scorecard["factors"]
        ranked.append(scored)

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return {
        "selected": ranked[0] if ranked else None,
        "ranked_options": ranked,
    }
