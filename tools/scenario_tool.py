SCENARIOS = {
    "cancelled": {
        "id": "cancelled",
        "name": "Flight cancelled",
        "summary": "Aircraft rotation disruption forces a full rebooking.",
        "status": {
            "status": "cancelled",
            "delay_minutes": 0,
            "reason": "Aircraft rotation disruption after severe weather in New York.",
        },
    },
    "short_delay": {
        "id": "short_delay",
        "name": "45 minute delay",
        "summary": "Manageable delay with enough connection buffer.",
        "status": {
            "status": "delayed",
            "delay_minutes": 45,
            "reason": "Late inbound aircraft.",
        },
    },
    "missed_connection": {
        "id": "missed_connection",
        "name": "Missed connection risk",
        "summary": "Delay erodes the protected transfer window.",
        "status": {
            "status": "delayed",
            "delay_minutes": 95,
            "reason": "Air traffic control ground delay.",
        },
    },
    "weather": {
        "id": "weather",
        "name": "Weather disruption",
        "summary": "Severe weather causes a long operational delay.",
        "status": {
            "status": "delayed",
            "delay_minutes": 180,
            "reason": "Thunderstorm cell over the departure corridor.",
        },
    },
    "overnight": {
        "id": "overnight",
        "name": "Overnight delay",
        "summary": "Late disruption creates service recovery needs.",
        "status": {
            "status": "delayed",
            "delay_minutes": 360,
            "reason": "Crew timeout after rolling departure delays.",
        },
    },
}


def list_scenarios():
    return list(SCENARIOS.values())


def get_scenario(scenario_id):
    return SCENARIOS.get(scenario_id, SCENARIOS["cancelled"])
