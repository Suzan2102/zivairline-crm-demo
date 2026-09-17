"""
Synthetic data generator for the ZivAirline CRM demo.

Run it with:      python -m zivair.seed_data
Optional flags:   --db PATH   --seed N

The script is deliberately written as a sequence of small `build_*` functions,
one per table, in dependency order. Every function returns the list of rows it
inserted so the next step can reuse them - no hidden global state.

Design notes
------------
* Dates are stored as ISO text ('YYYY-MM-DD HH:MM'), the usual SQLite practice.
* The flight window is anchored to the day the script runs, so the demo always
  has "yesterday", "today" and "next week" in it.
* `flights.seats_sold` counts every seat sold through every channel, while the
  `tickets` table only holds the passengers this agency booked. That is what a
  real agency CRM looks like: you see the whole aircraft, but you own a slice.
"""

from __future__ import annotations

import argparse
import random
import sqlite3
import string
from datetime import datetime, timedelta

from . import config, rules
from .database import connect, init_schema, table_counts
from .reference_data import (
    AGENTS,
    AIRPORTS,
    CUSTOMER_MARKETS,
    FIRST_NAMES,
    FLEET,
    INTERACTION_SUBJECTS,
    LAST_NAMES,
)

DT_FMT = "%Y-%m-%d %H:%M"
DATE_FMT = "%Y-%m-%d"

# Pricing and loyalty come from zivair/rules.py, so the demo data obeys exactly
# the same rules the booking screen will apply.
BAGGAGE_FEE = rules.BAGGAGE_FEE


# ---------------------------------------------------------------- helpers --
def _round_to_5(minutes: float) -> int:
    return int(round(minutes / 5.0) * 5)


def _pnr(rng: random.Random, taken: set[str]) -> str:
    """A 6-character booking reference, the way airlines actually do it."""
    alphabet = string.ascii_uppercase.replace("I", "").replace("O", "") + "0123456789"
    while True:
        code = "".join(rng.choice(alphabet) for _ in range(6))
        if code not in taken:
            taken.add(code)
            return code


def _seat_map(seats_economy: int, seats_business: int) -> dict[str, list[str]]:
    """Build the list of valid seat labels per cabin for one aircraft."""
    business_rows = max(1, seats_business // 4)
    business = [
        f"{row}{letter}"
        for row in range(1, business_rows + 1)
        for letter in "ACDF"
    ][:seats_business]

    first_economy_row = business_rows + 2  # leave a row for the galley
    economy = [
        f"{row}{letter}"
        for row in range(first_economy_row, first_economy_row + (seats_economy // 6) + 2)
        for letter in "ABCDEF"
    ][:seats_economy]

    return {"Business": business, "Economy": economy}


# ------------------------------------------------------------ master data --
def build_airports(conn: sqlite3.Connection) -> dict[str, dict]:
    rows = [(iata, name, city, country, region) for iata, name, city, country, region, _ in AIRPORTS]
    conn.executemany("INSERT INTO airports VALUES (?,?,?,?,?)", rows)
    return {
        iata: {"name": name, "city": city, "country": country, "region": region, "distance": dist}
        for iata, name, city, country, region, dist in AIRPORTS
    }


def build_aircraft(conn: sqlite3.Connection) -> list[dict]:
    conn.executemany("INSERT INTO aircraft VALUES (?,?,?,?,?,?,?)", FLEET)
    return [
        {
            "tail_number": tail,
            "model": model,
            "body_type": body,
            "seats_economy": eco,
            "seats_business": biz,
            "seats_total": eco + biz,
            "max_range_km": rng_km,
        }
        for tail, model, body, eco, biz, rng_km, _year in FLEET
    ]


def build_agents(conn: sqlite3.Connection) -> list[str]:
    conn.executemany("INSERT INTO agents VALUES (?,?,?,?,?)", AGENTS)
    return [a[0] for a in AGENTS]


def build_routes(conn: sqlite3.Connection, airports: dict[str, dict]) -> list[dict]:
    """Every route is a hub-and-spoke leg: TLV -> X or X -> TLV."""
    routes: list[dict] = []
    for iata, info in airports.items():
        if iata == config.HUB_AIRPORT:
            continue
        distance = info["distance"]
        duration = _round_to_5(30 + distance / 800 * 60)  # taxi + cruise at ~800 km/h
        for origin, destination in ((config.HUB_AIRPORT, iata), (iata, config.HUB_AIRPORT)):
            routes.append(
                {
                    "route_id": f"{origin}-{destination}",
                    "origin": origin,
                    "destination": destination,
                    "distance_km": distance,
                    "duration_minutes": duration,
                }
            )
    conn.executemany(
        "INSERT INTO routes VALUES (?,?,?,?,?)",
        [(r["route_id"], r["origin"], r["destination"], r["distance_km"], r["duration_minutes"])
         for r in routes],
    )
    return routes


def build_customers(conn: sqlite3.Connection, rng: random.Random, count: int) -> list[dict]:
    countries = [m[0] for m in CUSTOMER_MARKETS]
    weights = [m[2] for m in CUSTOMER_MARKETS]
    cities_by_country = {m[0]: m[1] for m in CUSTOMER_MARKETS}
    today = datetime.now()

    customers: list[dict] = []
    for i in range(1, count + 1):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        country = rng.choices(countries, weights=weights, k=1)[0]
        city = rng.choice(cities_by_country[country])

        age = int(rng.triangular(19, 78, 38))
        birth = today - timedelta(days=age * 365 + rng.randint(0, 364))
        member_since = today - timedelta(days=rng.randint(30, 8 * 365))

        # 12% business travellers, 3% VIP - they drive most of the revenue.
        segment = rng.choices(["Leisure", "Business", "VIP"], weights=[85, 12, 3], k=1)[0]

        customers.append(
            {
                "customer_id": f"CU-{i:05d}",
                "first_name": first,
                "last_name": last,
                "email": f"{first.lower()}.{last.lower()}{i}@example.com",
                "phone": f"+{rng.randint(1, 972)}-{rng.randint(20, 59)}-{rng.randint(1000000, 9999999)}",
                "birth_date": birth.strftime(DATE_FMT),
                "country": country,
                "city": city,
                "passport_number": f"{rng.choice(string.ascii_uppercase)}{rng.randint(10000000, 99999999)}",
                "loyalty_tier": "Basic",     # recalculated at the end from real activity
                "loyalty_points": 0,
                "member_since": member_since.strftime(DATE_FMT),
                "segment": segment,
                "marketing_optin": 1 if rng.random() < 0.62 else 0,
            }
        )

    conn.executemany(
        """INSERT INTO customers VALUES
           (:customer_id,:first_name,:last_name,:email,:phone,:birth_date,:country,:city,
            :passport_number,:loyalty_tier,:loyalty_points,:member_since,:segment,:marketing_optin)""",
        customers,
    )
    return customers


# ----------------------------------------------------------------- flights --
def build_flights(
    conn: sqlite3.Connection,
    rng: random.Random,
    routes: list[dict],
    fleet: list[dict],
) -> list[dict]:
    """
    One "rotation" per pick: an outbound leg from TLV plus its return leg,
    flown by the same aircraft after a turnaround on the ground.
    """
    outbound_routes = [r for r in routes if r["origin"] == config.HUB_AIRPORT]
    return_by_origin = {r["origin"]: r for r in routes if r["destination"] == config.HUB_AIRPORT}

    # Short leisure destinations get flown far more often than long haul.
    def popularity(route: dict) -> int:
        d = route["distance_km"]
        if d < 1500:
            return 10
        if d < 3000:
            return 7
        if d < 5000:
            return 4
        return 2

    weights = [popularity(r) for r in outbound_routes]

    # Stable flight numbers per route pair: ZV100/ZV101, ZV102/ZV103, ...
    flight_numbers: dict[str, str] = {}
    for idx, route in enumerate(sorted(outbound_routes, key=lambda r: r["route_id"])):
        flight_numbers[route["route_id"]] = f"{config.AIRLINE_CODE}{100 + idx * 2}"
        flight_numbers[return_by_origin[route["destination"]]["route_id"]] = (
            f"{config.AIRLINE_CODE}{101 + idx * 2}"
        )

    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    flights: list[dict] = []

    for day_offset in range(-config.DAYS_IN_PAST, config.DAYS_IN_FUTURE + 1):
        day = today + timedelta(days=day_offset)
        aircraft_used_today: set[str] = set()

        picked: list[dict] = []
        while len(picked) < config.FLIGHTS_PER_DAY:
            candidate = rng.choices(outbound_routes, weights=weights, k=1)[0]
            if candidate not in picked:
                picked.append(candidate)

        for route in picked:
            usable = [
                a
                for a in fleet
                if a["max_range_km"] >= route["distance_km"] * 1.15
                and a["tail_number"] not in aircraft_used_today
                and (a["body_type"] == "Wide-body" or route["distance_km"] < 6000)
            ]
            if not usable:
                continue
            plane = rng.choice(usable)
            aircraft_used_today.add(plane["tail_number"])

            depart_hour = rng.choice([6, 7, 8, 9, 10, 11, 13, 14, 16, 18, 20, 22])
            outbound_dep = day.replace(hour=depart_hour, minute=rng.choice([0, 5, 15, 25, 35, 45]))
            return_route = return_by_origin[route["destination"]]

            legs = [
                (route, outbound_dep),
                (
                    return_route,
                    outbound_dep
                    + timedelta(minutes=route["duration_minutes"] + rng.choice([90, 120, 150, 180])),
                ),
            ]

            for leg_route, departure in legs:
                arrival = departure + timedelta(minutes=leg_route["duration_minutes"])
                flight_number = flight_numbers[leg_route["route_id"]]
                flight_id = f"{flight_number}-{departure.strftime(DATE_FMT)}"
                if any(f["flight_id"] == flight_id for f in flights[-40:]):
                    continue  # the same rotation was already scheduled today

                status, delay = _flight_status(rng, departure, now)
                seats_total = plane["seats_total"]
                seats_sold = _seats_sold(rng, seats_total, departure, now, status)

                flights.append(
                    {
                        "flight_id": flight_id,
                        "flight_number": flight_number,
                        "route_id": leg_route["route_id"],
                        "tail_number": plane["tail_number"],
                        "departure_time": departure.strftime(DT_FMT),
                        "arrival_time": arrival.strftime(DT_FMT),
                        "status": status,
                        "delay_minutes": delay,
                        "gate": f"{rng.choice('ABCD')}{rng.randint(1, 24)}",
                        "seats_total": seats_total,
                        "seats_sold": seats_sold,
                        "base_fare": round(40 + leg_route["distance_km"] * 0.045 * rng.uniform(0.85, 1.25), 2),
                        # helper fields, not written to the DB:
                        "_departure_dt": departure,
                        "_distance": leg_route["distance_km"],
                        "_origin": leg_route["origin"],
                        "_destination": leg_route["destination"],
                        "_seats_economy": plane["seats_economy"],
                        "_seats_business": plane["seats_business"],
                    }
                )

    conn.executemany(
        """INSERT INTO flights VALUES
           (:flight_id,:flight_number,:route_id,:tail_number,:departure_time,:arrival_time,
            :status,:delay_minutes,:gate,:seats_total,:seats_sold,:base_fare)""",
        [{k: v for k, v in f.items() if not k.startswith("_")} for f in flights],
    )
    return flights


def _flight_status(rng: random.Random, departure: datetime, now: datetime) -> tuple[str, int]:
    """Derive an operational status from the departure time relative to now."""
    delayed = rng.random() < 0.22
    delay = rng.choice([15, 20, 30, 45, 60, 90, 120, 180]) if delayed else 0

    if rng.random() < 0.02:
        return "Cancelled", 0
    if departure < now - timedelta(hours=3):
        return "Landed", delay
    if departure < now:
        return "Departed", delay
    if departure < now + timedelta(hours=1):
        return "Boarding", delay
    if delayed and departure < now + timedelta(days=3):
        return "Delayed", delay
    return "Scheduled", delay


def _seats_sold(rng: random.Random, seats_total: int, departure: datetime,
                now: datetime, status: str) -> int:
    """
    Final load factor is 70-97%. Future flights are only partially sold:
    the closer to departure, the fuller the aircraft (a booking curve).
    """
    if status == "Cancelled":
        return 0
    final_load = rng.uniform(0.70, 0.97)
    days_out = (departure - now).days
    if days_out <= 0:
        progress = 1.0
    else:
        progress = min(1.0, 0.35 + 0.65 * (1 - days_out / max(config.DAYS_IN_FUTURE, 1)))
    return int(seats_total * final_load * progress)


# ------------------------------------------------- bookings and tickets --
def build_bookings(
    conn: sqlite3.Connection,
    rng: random.Random,
    flights: list[dict],
    customers: list[dict],
    agent_ids: list[str],
) -> tuple[list[dict], list[dict]]:
    """
    Bookings are generated from the outbound (TLV departure) flights only;
    a share of them get a matching return leg, producing a round trip.
    """
    now = datetime.now()
    by_id = {f["flight_id"]: f for f in flights}
    outbound = [f for f in flights if f["_origin"] == config.HUB_AIRPORT]

    # Index of return flights, so a round trip can find its way home.
    returns_from: dict[str, list[dict]] = {}
    for f in flights:
        if f["_destination"] == config.HUB_AIRPORT:
            returns_from.setdefault(f["_origin"], []).append(f)

    used_seats: dict[str, set[str]] = {}
    seat_maps: dict[str, dict[str, list[str]]] = {}
    for f in flights:
        seat_maps[f["flight_id"]] = _seat_map(f["_seats_economy"], f["_seats_business"])
        used_seats[f["flight_id"]] = set()

    # Frequent flyers should show up again and again, so weight the draw.
    customer_weights = [
        {"Leisure": 1.0, "Business": 3.0, "VIP": 5.0}[c["segment"]] for c in customers
    ]

    bookings: list[dict] = []
    tickets: list[dict] = []
    taken_pnrs: set[str] = set()
    ticket_seq = 0

    for flight in outbound:
        if flight["status"] == "Cancelled" and rng.random() < 0.5:
            continue
        # The agency owns 4-12% of the cabin on each flight.
        pax_count = max(3, int(flight["seats_total"] * rng.uniform(0.04, 0.12)))

        for _ in range(pax_count):
            customer = rng.choices(customers, weights=customer_weights, k=1)[0]
            legs = [flight]

            # 55% of outbound trips come back with us within two weeks.
            if rng.random() < 0.55:
                candidates = [
                    r
                    for r in returns_from.get(flight["_destination"], [])
                    if 1 <= (r["_departure_dt"] - flight["_departure_dt"]).days <= 14
                ]
                if candidates:
                    legs.append(rng.choice(candidates))

            booking_dt = _booking_date(rng, flight["_departure_dt"], customer, now)
            if booking_dt is None:
                continue  # not booked yet, or not a customer back then

            cabin = _pick_cabin(rng, customer)
            channel = _pick_channel(rng, customer)
            agent_id = (
                rng.choice(agent_ids)
                if channel in ("Travel Agent", "Call Center", "Partner")
                else None
            )

            booking_id = _pnr(rng, taken_pnrs)
            booking_tickets: list[dict] = []

            for leg in legs:
                seat_pool = seat_maps[leg["flight_id"]][cabin]
                free = [s for s in seat_pool if s not in used_seats[leg["flight_id"]]]
                if not free:
                    continue
                seat = rng.choice(free)
                used_seats[leg["flight_id"]].add(seat)

                ticket_seq += 1
                lead_days = max((leg["_departure_dt"] - booking_dt).days, 0)
                fare = rules.quote_fare(
                    leg["base_fare"], cabin, lead_days, customer["loyalty_tier"]
                )
                status = _ticket_status(rng, leg, now)
                booking_tickets.append(
                    {
                        "ticket_id": f"TK-{ticket_seq:06d}",
                        "booking_id": booking_id,
                        "flight_id": leg["flight_id"],
                        "cabin": cabin,
                        "seat": seat,
                        "fare": fare,
                        "baggage_count": rng.choices([0, 1, 2], weights=[25, 55, 20], k=1)[0],
                        "checked_in": 1 if status == "Flown" or leg["status"] == "Boarding" else 0,
                        "status": status,
                        "_distance": leg["_distance"],
                    }
                )

            if not booking_tickets:
                continue

            statuses = {t["status"] for t in booking_tickets}
            if statuses == {"Cancelled"}:
                booking_status, payment = "Cancelled", "Refunded"
            elif statuses == {"Flown"}:
                booking_status, payment = "Completed", "Paid"
            else:
                booking_status = "Confirmed"
                payment = rng.choices(["Paid", "Pending"], weights=[92, 8], k=1)[0]

            ancillaries = sum(t["baggage_count"] * BAGGAGE_FEE for t in booking_tickets)
            total = sum(t["fare"] for t in booking_tickets) + ancillaries

            bookings.append(
                {
                    "booking_id": booking_id,
                    "customer_id": customer["customer_id"],
                    "agent_id": agent_id,
                    "booking_date": booking_dt.strftime(DT_FMT),
                    "channel": channel,
                    "status": booking_status,
                    "payment_status": payment,
                    "total_amount": round(total, 2),
                    "currency": config.CURRENCY,
                    "notes": _booking_note(rng, customer, cabin),
                }
            )
            tickets.extend(booking_tickets)

    conn.executemany(
        """INSERT INTO bookings VALUES
           (:booking_id,:customer_id,:agent_id,:booking_date,:channel,:status,
            :payment_status,:total_amount,:currency,:notes)""",
        bookings,
    )
    conn.executemany(
        """INSERT INTO tickets VALUES
           (:ticket_id,:booking_id,:flight_id,:cabin,:seat,:fare,:baggage_count,
            :checked_in,:status)""",
        [{k: v for k, v in t.items() if not k.startswith("_")} for t in tickets],
    )
    return bookings, tickets


def _pick_cabin(rng: random.Random, customer: dict) -> str:
    odds = {"Leisure": 0.04, "Business": 0.35, "VIP": 0.70}[customer["segment"]]
    return "Business" if rng.random() < odds else "Economy"


def _pick_channel(rng: random.Random, customer: dict) -> str:
    if customer["segment"] in ("Business", "VIP"):
        return rng.choices(
            config.BOOKING_CHANNELS, weights=[20, 10, 45, 20, 5], k=1
        )[0]
    return rng.choices(config.BOOKING_CHANNELS, weights=[42, 28, 15, 10, 5], k=1)[0]


def _booking_date(rng: random.Random, departure: datetime, customer: dict,
                  now: datetime) -> datetime | None:
    """
    When this passenger booked - or None if they have not booked yet.

    Returning None is what produces the booking curve: a passenger whose draw
    lands in the future simply has not walked into the agency yet, so a flight
    three months out ends up only lightly sold. Clamping the date to "now"
    instead would pile every one of those bookings onto today.
    """
    lead = int(rng.triangular(1, 150, 28))
    booked = departure - timedelta(days=lead, hours=rng.randint(0, 23))
    if booked > now:
        return None
    if booked < datetime.strptime(customer["member_since"], DATE_FMT):
        return None  # they were not a customer of ours yet
    return booked


def _ticket_status(rng: random.Random, flight: dict, now: datetime) -> str:
    if flight["status"] == "Cancelled":
        return "Cancelled"
    if flight["_departure_dt"] < now:
        return "Flown"
    return "Cancelled" if rng.random() < 0.06 else "Confirmed"


def _booking_note(rng: random.Random, customer: dict, cabin: str) -> str | None:
    pool = ["Window seat requested", "Vegetarian meal", "Wheelchair assistance",
            "Travelling with an infant", "Extra legroom paid", "Corporate contract fare"]
    if customer["segment"] == "VIP":
        pool += ["Lounge access confirmed", "Priority boarding arranged"]
    if cabin == "Business":
        pool += ["Chauffeur pickup booked"]
    return rng.choice(pool) if rng.random() < 0.30 else None


# ------------------------------------------------------------ interactions --
def build_interactions(
    conn: sqlite3.Connection,
    rng: random.Random,
    customers: list[dict],
    bookings: list[dict],
    agent_ids: list[str],
    count: int = 700,
) -> list[dict]:
    now = datetime.now()
    bookings_by_customer: dict[str, list[str]] = {}
    for b in bookings:
        bookings_by_customer.setdefault(b["customer_id"], []).append(b["booking_id"])

    # Only customers who actually flew generate service traffic.
    active = [c for c in customers if c["customer_id"] in bookings_by_customer] or customers

    interactions: list[dict] = []
    for i in range(1, count + 1):
        customer = rng.choice(active)
        topic = rng.choices(
            config.INTERACTION_TYPES, weights=[25, 22, 15, 14, 12, 12], k=1
        )[0]
        created = now - timedelta(days=rng.randint(0, 90), hours=rng.randint(0, 23))
        priority = rng.choices(config.PRIORITIES, weights=[35, 45, 20], k=1)[0]
        status = rng.choices(config.INTERACTION_STATUSES, weights=[18, 17, 65], k=1)[0]
        resolved = (
            (created + timedelta(hours=rng.randint(1, 96))).strftime(DT_FMT)
            if status == "Resolved"
            else None
        )
        related = bookings_by_customer.get(customer["customer_id"])

        interactions.append(
            {
                "interaction_id": f"IN-{i:05d}",
                "customer_id": customer["customer_id"],
                "booking_id": rng.choice(related) if related and rng.random() < 0.75 else None,
                "agent_id": rng.choice(agent_ids),
                "created_at": created.strftime(DT_FMT),
                "channel": rng.choices(config.INTERACTION_CHANNELS, weights=[40, 30, 20, 10], k=1)[0],
                "topic": topic,
                "subject": rng.choice(INTERACTION_SUBJECTS[topic]),
                "priority": priority,
                "status": status,
                "resolved_at": resolved,
            }
        )

    conn.executemany(
        """INSERT INTO interactions VALUES
           (:interaction_id,:customer_id,:booking_id,:agent_id,:created_at,:channel,
            :topic,:subject,:priority,:status,:resolved_at)""",
        interactions,
    )
    return interactions


# ----------------------------------------------------------------- loyalty --
def apply_loyalty(conn: sqlite3.Connection, rng: random.Random,
                  customers: list[dict], bookings: list[dict], tickets: list[dict]) -> None:
    """Points come from flown tickets, plus a legacy balance; tier follows points."""
    customer_by_booking = {b["booking_id"]: b["customer_id"] for b in bookings}
    points: dict[str, int] = {c["customer_id"]: 0 for c in customers}

    for t in tickets:
        if t["status"] != "Flown":
            continue
        customer_id = customer_by_booking.get(t["booking_id"])
        if customer_id is None:
            continue
        points[customer_id] += rules.points_for_flight(t["_distance"], t["cabin"])

    updates = []
    for c in customers:
        legacy = int(rng.triangular(0, 5000, 400))
        total = points[c["customer_id"]] + legacy
        updates.append((total, rules.tier_for_points(total), c["customer_id"]))

    conn.executemany(
        "UPDATE customers SET loyalty_points = ?, loyalty_tier = ? WHERE customer_id = ?",
        updates,
    )


# -------------------------------------------------------------------- main --
def generate(db_path=config.DB_PATH, seed: int = config.RANDOM_SEED) -> dict[str, int]:
    rng = random.Random(seed)
    conn = connect(db_path)
    try:
        init_schema(conn)
        airports = build_airports(conn)
        fleet = build_aircraft(conn)
        agent_ids = build_agents(conn)
        routes = build_routes(conn, airports)
        customers = build_customers(conn, rng, config.NUM_CUSTOMERS)
        flights = build_flights(conn, rng, routes, fleet)
        bookings, tickets = build_bookings(conn, rng, flights, customers, agent_ids)
        build_interactions(conn, rng, customers, bookings, agent_ids)
        apply_loyalty(conn, rng, customers, bookings, tickets)
        conn.commit()
    finally:
        conn.close()
    return table_counts(db_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the ZivAirline CRM demo database.")
    parser.add_argument("--db", default=str(config.DB_PATH), help="output database path")
    parser.add_argument("--seed", type=int, default=config.RANDOM_SEED, help="random seed")
    args = parser.parse_args()

    from pathlib import Path

    db_path = Path(args.db)
    print(f"Generating {config.AIRLINE_NAME} demo data -> {db_path}")
    counts = generate(db_path, args.seed)
    width = max(len(name) for name in counts)
    for name, n in sorted(counts.items()):
        print(f"  {name.ljust(width)}  {n:>7,}")
    print("Done.")


if __name__ == "__main__":
    main()
