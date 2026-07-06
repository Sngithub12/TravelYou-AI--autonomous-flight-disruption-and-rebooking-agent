from datetime import datetime, timedelta


def preview_connection_risk(booking):
    """A static, pre-disruption risk label — no actual delay has happened
    yet, this just characterizes how much margin the passenger has if one
    does. Used in the UI to show risk profile before running the agent,
    not a replacement for assess_disruption_impact (which reacts to a
    real delay)."""
    if "connection_departure" not in booking or "minimum_connection_minutes" not in booking:
        return {"label": "No onward connection", "level": "none"}

    arrival = datetime.fromisoformat(booking["arrival_time"])
    connection_departure = datetime.fromisoformat(booking["connection_departure"])
    buffer_minutes = int((connection_departure - arrival).total_seconds() / 60)
    minimum_required = booking["minimum_connection_minutes"]
    margin = buffer_minutes - minimum_required

    if margin <= 15:
        return {"label": f"Tight connection ({buffer_minutes} min buffer)", "level": "high"}
    elif margin <= 60:
        return {"label": f"Moderate buffer ({buffer_minutes} min)", "level": "medium"}
    else:
        return {"label": f"Comfortable buffer ({buffer_minutes} min)", "level": "low"}


def assess_disruption_impact(booking, status):
    original_arrival = datetime.fromisoformat(booking["arrival_time"])
    delay_minutes = status.get("delay_minutes", 0)
    delayed_arrival = original_arrival + timedelta(minutes=delay_minutes)

    has_connection = "connection_departure" in booking and "minimum_connection_minutes" in booking
    if has_connection:
        connection_departure = datetime.fromisoformat(booking["connection_departure"])
        connection_buffer = int((connection_departure - original_arrival).total_seconds() / 60)
        projected_buffer = connection_buffer - delay_minutes
        missed_connection = projected_buffer < booking["minimum_connection_minutes"]
    else:
        connection_buffer = None
        projected_buffer = None
        missed_connection = False

    if status["status"] == "cancelled":
        severity = "critical"
        reason = "The operating flight was cancelled."
    elif missed_connection:
        severity = "high"
        reason = "The delay creates a high risk of missing the onward connection."
    elif delay_minutes >= 90:
        severity = "medium"
        reason = "The delay materially changes the passenger arrival plan."
    else:
        severity = "low"
        reason = "The disruption appears manageable without rebooking."

    return {
        "severity": severity,
        "reason": reason,
        "missed_connection": missed_connection,
        "connection_buffer_minutes": connection_buffer,
        "projected_buffer_minutes": projected_buffer,
        # A cancelled flight never departed, so it has no real delayed-arrival time.
        "delayed_arrival": None if status["status"] == "cancelled" else delayed_arrival.isoformat(),
    }