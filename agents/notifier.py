from config import Config
from llm.openrouter import generate_notification_with_llm


def build_customer_notification(booking, status, impact, selection):
    selected = selection["selected"]

    if Config.USE_LLM_NOTIFICATIONS and Config.OPENROUTER_API_KEY:
        llm_message = generate_notification_with_llm(booking, status, impact, selected)
        if llm_message:
            return llm_message

    return (
        f"Hi {booking['passenger']['name']}, your flight {booking['flight_number']} "
        f"from {booking['origin']} to {booking['destination']} was {status['status']}. "
        f"TripMind AI selected {selected['flight_number']} on {selected['airline']}, "
        f"departing {selected['departure_time']} and arriving {selected['arrival_time']}. "
        f"This option was chosen because it protects your connection, keeps the delay low, "
        f"and best matches your travel preferences. Your new seat preference is marked as "
        f"{selected['seat_available']} where available."
    )
