# ZivAirline CRM

A CRM for the travel agents of **ZivAirline** — track flights, manage customers, and
handle the bookings that connect the two. Built with **Streamlit** on top of a
**SQLite** database filled with synthetic but realistic airline data.

> Teaching demo. Every customer, booking and flight in this repository is generated
> by `zivair/seed_data.py` — no real personal data is involved.

---

## What it does

| Area | Question it answers |
|------|---------------------|
| **Dashboard** | How is the airline doing right now? Load factor, revenue, on-time performance, open service cases. |
| **Flights** | Which flights are scheduled, delayed or cancelled — and who is on board? |
| **Customers** | Who is this passenger, what is their history and how valuable are they? |
| **Bookings** | Book a customer onto a flight, change a seat, check them in, cancel a trip. |
| **Reports** | Revenue by route, channel mix, loyalty distribution, agent performance. |

---

## Quick start

```bash
# 1. install dependencies
pip install -r requirements.txt

# 2. generate the demo database (data/zivairline.db)
python -m zivair.seed_data

# 3. run the app
streamlit run app.py
```

The app opens at <http://localhost:8501>.

Regenerating the data is always safe — `seed_data.py` drops and rebuilds every table:

```bash
python -m zivair.seed_data --seed 7      # a different random world
python -m zivair.seed_data --db /tmp/x.db  # write somewhere else
```

---

## Screenshots

*Added as each phase is completed.*

<!-- SCREENSHOTS -->

---

## Project layout

```
crm/
├── app.py                    # Streamlit entry point
├── requirements.txt
├── data/
│   └── zivairline.db         # generated, not committed
└── zivair/
    ├── config.py             # paths, constants, business vocabulary
    ├── schema.sql            # the whole data model, commented
    ├── database.py           # connection + query helpers (no domain logic)
    ├── reference_data.py     # airports, fleet, agents, name pools
    └── seed_data.py          # the synthetic data generator
```

---

## The data model

Nine tables. The interesting one is `tickets` — it is the many-to-many join that
turns a *customer* and a *flight* into a *seat*.

```
airports ──< routes >── airports
                │
                ▼
aircraft ──> flights <── tickets ──> bookings ──> customers
                                         │            │
                                       agents      interactions
```

| Table | Rows (default seed) | Holds |
|-------|--------------------:|-------|
| `airports` | 23 | The network ZivAirline serves, hub = TLV |
| `aircraft` | 14 | The fleet, with per-cabin seat counts |
| `agents` | 6 | The people using this CRM |
| `routes` | 44 | Every hub leg, both directions, with distance |
| `customers` | 900 | Passengers, loyalty tier, segment, market |
| `flights` | ~600 | 45 days back, 30 days forward, with live status |
| `bookings` | ~5,000 | A PNR: who booked, through which channel, for how much |
| `tickets` | ~7,300 | One passenger on one flight, with a seat |
| `interactions` | 700 | The service log: complaints, changes, refunds |

**Two details worth knowing:**

- `flights.seats_sold` counts seats sold through *every* channel, while `tickets`
  only holds the passengers **this agency** booked. That is what an agency CRM
  really looks like: you see the whole aircraft, but you own a slice of it.
- The flight window is anchored to the day you run the generator, so the demo
  always contains yesterday, today and next week.

---

## How the data is made realistic

The generator is not just `random.choice` everywhere. It encodes real airline behaviour:

- **Booking curve** — a flight 30 days out is ~35% sold; the same flight tomorrow is ~100% sold.
- **Fare ladder** — book 90 days ahead and pay 0.82× the base fare; book the day before and pay 1.45×.
- **Fleet assignment** — a 9,100 km leg to JFK can only be flown by a wide-body with the range for it.
- **Loyalty follows activity** — points are earned per flown kilometre (business ×2), and the
  tier is derived from the points, producing a realistic pyramid rather than a flat split.
- **Segment drives behaviour** — business and VIP customers fly more often, book business class
  more often, and reach the agent through the call centre rather than the website.

---

## Development phases

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Data model, synthetic data generator, documentation | ✅ Done |
| 2 | Query layer, app shell, Dashboard | ⬜ |
| 3 | Flights module + passenger manifest | ⬜ |
| 4 | Customers module + 360° customer card | ⬜ |
| 5 | Bookings module (create / change / check-in / cancel) | ⬜ |
| 6 | Reports, polish, final documentation | ⬜ |

Full documentation lives in the Obsidian vault under `ZivAirline-CRM/`.

---

## Requirements

Python 3.10+, plus `streamlit`, `pandas`, `plotly`. See `requirements.txt`.
