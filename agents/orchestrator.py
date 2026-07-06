from agents.decision import choose_best_itinerary
from agents.notifier import build_customer_notification
from agents.planner import assess_disruption_impact
from llm.openrouter import generate_text_with_llm
from tools.booking_tool import get_booking
from tools.flight_status import get_flight_status
from tools.logger import log_event
from tools.scenario_tool import get_scenario
from tools.search_flights import search_alternative_flights


class TripMindOrchestrator:
    """Runs one disruption-recovery session. Instantiate fresh per request.

    Hybrid design: the TOOL CALL SEQUENCE is fixed in Python — deterministic,
    can't be skipped or reordered by a small/unreliable model. But the LLM is
    still genuinely in the loop: at each decision point it's asked to
    interpret the real tool output and explain its reasoning in its own
    words, and finalize_recovery's notification is LLM-generated. This
    trades "the LLM freely picks which tool to call next" for "the LLM
    reasons about real data at every step" — which is far more reliable
    across model sizes (verified: 1B-class models drop or hallucinate steps
    in a free-form tool-calling loop, but handle single-shot reasoning
    prompts over real data fine).
    """

    def __init__(self, scenario_id=None, booking_id=None):
        self.scenario_id = scenario_id or "cancelled"
        self.booking_id = booking_id  # None -> booking_tool's own default
        self.state = {}
        self.trace = []

    # Phrases that indicate the model went off-topic into a refusal or
    # disclaimer unrelated to the actual prompt — small models occasionally
    # misfire this way even on completely benign inputs.
    _REFUSAL_MARKERS = (
        "i cannot provide", "i can't provide", "i'm not able to", "i am not able to",
        "as an ai", "illegal", "harmful activities", "i'm sorry, but",
    )

    def _log(self, entry_type, title, content):
        entry = {"type": entry_type, "title": title, "content": content}
        self.trace.append(entry)
        log_event(f"[{entry_type.upper()}] {title}", content)

    def _is_untrustworthy(self, text, must_mention):
        if not text:
            return True
        lowered = text.lower()
        if any(marker in lowered for marker in self._REFUSAL_MARKERS):
            return True
        if must_mention and not any(str(term).lower() in lowered for term in must_mention if term):
            return True
        return False

    def _reason(self, prompt, fallback, must_mention=None):
        text = generate_text_with_llm(prompt, fallback=fallback)
        if self._is_untrustworthy(text, must_mention):
            log_event("Discarded ungrounded/refusal reasoning, using fallback", {"raw": text})
            text = fallback
        self._log("reasoning", "Agent reasoning", text)
        return text

    def handle_disruption(self):
        # Step 1 — get_booking
        self._log("tool_call", "Calling get_booking", {"booking_id": self.booking_id})
        booking = get_booking(self.booking_id)
        self.state["booking"] = booking
        self._log("tool_result", "Result from get_booking", booking)

        # Step 2 — get_flight_status
        flight_number = booking["flight_number"]
        self._log("tool_call", "Calling get_flight_status", {"flight_number": flight_number})
        baseline = get_flight_status(flight_number)
        scenario = get_scenario(self.scenario_id)
        status = {**baseline, **scenario["status"]}
        self.state["status"] = status
        self.state["scenario"] = scenario
        self._log("tool_result", "Result from get_flight_status", status)

        self._reason(
            f"In one sentence, explain what it means for the passenger that flight "
            f"{flight_number} is now '{status['status']}' "
            f"(delay: {status.get('delay_minutes', 0)} minutes).",
            fallback=f"Flight {flight_number} status changed to {status['status']}.",
            must_mention=[flight_number],
        )

        # Step 3 — assess_disruption_impact
        self._log("tool_call", "Calling assess_disruption_impact", {})
        impact = assess_disruption_impact(booking, status)
        self.state["impact"] = impact
        self._log("tool_result", "Result from assess_disruption_impact", impact)

        self._reason(
            f"In one sentence, explain the severity of this situation for the "
            f"passenger: {impact['reason']} Missed connection risk: {impact['missed_connection']}.",
            fallback=impact["reason"],
            must_mention=[impact["severity"]],
        )

        selection = {"selected": None, "ranked_options": []}
        if impact["severity"] != "low":
            # Step 4 — search_alternative_flights
            self._log(
                "tool_call", "Calling search_alternative_flights",
                {"origin": booking["origin"], "destination": booking["destination"], "date": booking["date"]},
            )
            alternatives = search_alternative_flights(booking["origin"], booking["destination"], booking["date"])
            self.state["alternatives"] = alternatives
            self._log("tool_result", "Result from search_alternative_flights", alternatives)

            # Step 5 — choose_best_itinerary
            self._log("tool_call", "Calling choose_best_itinerary", {})
            selection = choose_best_itinerary(alternatives, booking["passenger"])
            self.state["selection"] = selection
            self._log("tool_result", "Result from choose_best_itinerary", selection)

            if selection["selected"]:
                top = selection["selected"]
                self._reason(
                    f"In one sentence, justify why {top['airline']} {top['flight_number']} "
                    f"(score {top['score']}) is the best rebooking choice for a "
                    f"{booking['passenger']['preferred_airline']}-preferring, "
                    f"{booking['passenger']['seat_preference']}-seat passenger, "
                    f"versus the other ranked options.",
                    fallback=f"{top['airline']} {top['flight_number']} scored highest on timing, cost, and preference fit.",
                    must_mention=[top["flight_number"]],
                )
            else:
                self._reason(
                    "No valid alternative flights were found for this route and date. "
                    "In one sentence, state that this is being escalated to manual review.",
                    fallback="No suitable alternatives found — escalating to manual review.",
                )
        else:
            self._reason(
                "The disruption is low severity and doesn't require rebooking. "
                "In one sentence, state that the situation will be monitored.",
                fallback="Disruption is manageable without rebooking; monitoring only.",
            )

        # Step 6 — finalize_recovery
        self._log("tool_call", "Calling finalize_recovery", {})
        selected = selection["selected"]
        if selected is None:
            service_recovery = {
                "action": "Escalate to manual review" if impact["severity"] != "low" else "Monitor only",
                "voucher": "N/A",
                "new_pnr": None,
                "ticket_status": "Pending manual action" if impact["severity"] != "low" else "No action needed",
            }
        else:
            service_recovery = self._build_service_recovery(status, impact, selected)

        notification = build_customer_notification(booking, status, impact, selection)
        self.state["service_recovery"] = service_recovery
        self.state["notification"] = notification
        self._log("tool_result", "Result from finalize_recovery",
                   {"service_recovery": service_recovery, "notification": notification})
        self._log("final", "Agent decision", notification)

        log_event("TravelYou agent completed disruption workflow", {"selected": selected})

        return {
            "scenario": scenario,
            "booking": booking,
            "status": status,
            "impact": impact,
            "selection": selection,
            "notification": notification,
            "service_recovery": service_recovery,
            "agent_steps": [t["title"] for t in self.trace if t["type"] in ("tool_call", "final")],
            "trace": self.trace,
        }

    def _build_service_recovery(self, status, impact, selected):
        if status["status"] == "cancelled" or impact.get("missed_connection"):
            action, voucher = "Auto-hold replacement itinerary", "Meal voucher eligible"
        elif status.get("delay_minutes", 0) >= 180:
            action, voucher = "Recommend rebooking approval", "Meal and lounge voucher eligible"
        elif status.get("delay_minutes", 0) >= 90:
            action, voucher = "Notify passenger with protected option", "No voucher triggered"
        else:
            action, voucher = "Monitor only", "No voucher triggered"
        return {
            "action": action,
            "voucher": voucher,
            "new_pnr": f"TM{selected['flight_number'].replace('-', '')[-4:]}9K",
            "ticket_status": "Held for passenger confirmation",
        }
