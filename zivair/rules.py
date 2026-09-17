"""
Business rules, in one place.

These are the decisions the airline made, not facts about the data: what a fare
costs, when a passenger becomes a Gold member, whether a flight can still be
booked. They live here rather than inside the generator or a screen, because the
same rule has to hold in all three - the demo data, the booking form, and the
reports must agree, or the app contradicts itself.
"""

from __future__ import annotations

from datetime import datetime

# --- Loyalty ---------------------------------------------------------------
# Points are earned per flown kilometre (see points_for_flight), so the
# thresholds are in points, not in flights.
TIER_THRESHOLDS = [("Platinum", 30000), ("Gold", 16000), ("Silver", 7500), ("Basic", 0)]

TIER_ORDER = ["Basic", "Silver", "Gold", "Platinum"]


def tier_for_points(points: int) -> str:
    """A tier is *derived* from points - never chosen by hand (rule BR-6)."""
    for tier, threshold in TIER_THRESHOLDS:
        if points >= threshold:
            return tier
    return "Basic"


def points_to_next_tier(points: int) -> tuple[str | None, int]:
    """(next tier, points still needed). (None, 0) once the top tier is reached."""
    current = tier_for_points(points)
    if current == TIER_ORDER[-1]:
        return None, 0
    nxt = TIER_ORDER[TIER_ORDER.index(current) + 1]
    threshold = dict((t, p) for t, p in TIER_THRESHOLDS)[nxt]
    return nxt, threshold - points


def points_for_flight(distance_km: int, cabin: str) -> int:
    """Half a point per kilometre in economy, double that in business."""
    multiplier = 2.0 if cabin == "Business" else 1.0
    return int(distance_km * multiplier / 2)


# --- Pricing ---------------------------------------------------------------
CABIN_MULTIPLIER = {"Economy": 1.0, "Business": 3.2}
TIER_DISCOUNT = {"Basic": 1.00, "Silver": 0.97, "Gold": 0.94, "Platinum": 0.90}
BAGGAGE_FEE = 35.0


def lead_time_multiplier(days_before_departure: int) -> float:
    """Buy early, pay less - the classic airline revenue curve."""
    if days_before_departure >= 90:
        return 0.82
    if days_before_departure >= 45:
        return 0.90
    if days_before_departure >= 21:
        return 1.00
    if days_before_departure >= 7:
        return 1.18
    return 1.45


def quote_fare(base_fare: float, cabin: str, days_before_departure: int,
               loyalty_tier: str) -> float:
    """What one ticket costs. Used by the generator and by the booking form."""
    price = (
        base_fare
        * CABIN_MULTIPLIER[cabin]
        * lead_time_multiplier(max(days_before_departure, 0))
        * TIER_DISCOUNT.get(loyalty_tier, 1.0)
    )
    return round(price, 2)


# --- Operational -----------------------------------------------------------
BOOKABLE_FLIGHT_STATUSES = {"Scheduled", "Delayed"}


def is_bookable(flight_status: str, departure_time: str,
                now: datetime | None = None) -> bool:
    """
    Rule BR-2: a passenger cannot be added to a flight that has left or been
    cancelled. Boarding flights are closed too - the gate is already working.
    """
    if flight_status not in BOOKABLE_FLIGHT_STATUSES:
        return False
    departure = datetime.strptime(departure_time, "%Y-%m-%d %H:%M")
    return departure > (now or datetime.now())
