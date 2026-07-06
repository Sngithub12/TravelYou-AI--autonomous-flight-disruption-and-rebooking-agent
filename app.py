import os

from flask import Flask, render_template, request

from agents.orchestrator import TripMindOrchestrator
from agents.planner import preview_connection_risk
from config import Config
from tools.booking_tool import get_booking, list_bookings
from tools.scenario_tool import list_scenarios


app = Flask(__name__)
app.config.from_object(Config)

FEATURED_BOOKING_IDS = ["TM-24662", "TM-80284"]  # Cristian Santos (tight, 45-min buffer) vs Noah Rhodes (comfortable, 150-min buffer)

@app.get("/")
def index():
    default_booking = get_booking(None)
    all_bookings = list_bookings()
    for b in all_bookings:
        b["risk_preview"] = preview_connection_risk(b)
    featured = [b for b in all_bookings if b["booking_id"] in FEATURED_BOOKING_IDS]
    return render_template(
        "index.html",
        scenarios=list_scenarios(),
        bookings=featured or all_bookings,
        booking=default_booking,
    )



@app.post("/run-agent")
def run_agent():
    scenario_id = request.form.get("scenario", "cancelled")
    booking_id = request.form.get("booking_id")  # None -> booking_tool's own default
    try:
        result = TripMindOrchestrator(scenario_id=scenario_id, booking_id=booking_id).handle_disruption()
        return render_template("result.html", result=result, error=None)
    except Exception as exc:
        app.logger.exception("Agent run failed")
        return render_template("result.html", result=None, error=str(exc)), 500


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
## at the bottom of app.py, replace app.run(...) with:
#from waitress import serve
#serve(app, host="127.0.0.1", port=5001)
#