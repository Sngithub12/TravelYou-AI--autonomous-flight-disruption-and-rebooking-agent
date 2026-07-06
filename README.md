# TripMind AI

Autonomous flight disruption and rebooking agent prototype.

TripMind AI monitors a disrupted itinerary, reasons about passenger impact, searches replacement flights through tool modules, selects the best itinerary, and generates a customer notification.

## Run locally

```powershell
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Agent flow

1. Load passenger booking from `mock_data/booking.json`.
2. Check disruption status through `tools/flight_status.py`.
3. Assess connection risk and disruption severity in `agents/planner.py`.
4. Search replacement flights through `tools/search_flights.py`.
5. Rank options in `agents/decision.py`.
6. Generate the customer notification in `agents/notifier.py`.

## LLM notifications

The app works without an LLM by default. To use OpenRouter for generated notifications:

```env
OPENROUTER_API_KEY=your_key
USE_LLM_NOTIFICATIONS=true
```

The OpenRouter wrapper is in `llm/openrouter.py`.
