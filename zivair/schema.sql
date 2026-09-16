-- ============================================================================
-- ZivAirline CRM - database schema (SQLite)
-- ----------------------------------------------------------------------------
-- Reading order (dependencies flow downwards):
--   airports, aircraft, agents, customers   -> reference / master data
--   routes      -> two airports
--   flights     -> a route + an aircraft
--   bookings    -> a customer (+ the agent who opened it)
--   tickets     -> a booking + a flight   (the many-to-many join in the middle)
--   interactions-> a customer (+ optionally a booking)
-- ============================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS interactions;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS flights;
DROP TABLE IF EXISTS routes;
DROP TABLE IF EXISTS aircraft;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS agents;
DROP TABLE IF EXISTS airports;

-- ---------------------------------------------------------------- airports --
CREATE TABLE airports (
    iata        TEXT PRIMARY KEY,               -- 'TLV'
    name        TEXT NOT NULL,
    city        TEXT NOT NULL,
    country     TEXT NOT NULL,
    region      TEXT NOT NULL                   -- Europe / Middle East / ...
);

-- ---------------------------------------------------------------- aircraft --
CREATE TABLE aircraft (
    tail_number     TEXT PRIMARY KEY,           -- '4X-ZVA'
    model           TEXT NOT NULL,
    body_type       TEXT NOT NULL CHECK (body_type IN ('Narrow-body', 'Wide-body')),
    seats_economy   INTEGER NOT NULL,
    seats_business  INTEGER NOT NULL,
    max_range_km    INTEGER NOT NULL,
    year_built      INTEGER NOT NULL
);

-- ------------------------------------------------------------------ agents --
-- The travel agents who operate this CRM.
CREATE TABLE agents (
    agent_id    TEXT PRIMARY KEY,               -- 'AG-01'
    full_name   TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    team        TEXT NOT NULL,                  -- Sales / Service / Corporate
    hired_on    TEXT NOT NULL
);

-- --------------------------------------------------------------- customers --
CREATE TABLE customers (
    customer_id     TEXT PRIMARY KEY,           -- 'CU-00001'
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    phone           TEXT NOT NULL,
    birth_date      TEXT NOT NULL,
    country         TEXT NOT NULL,
    city            TEXT NOT NULL,
    passport_number TEXT NOT NULL,
    loyalty_tier    TEXT NOT NULL CHECK (loyalty_tier IN ('Basic','Silver','Gold','Platinum')),
    loyalty_points  INTEGER NOT NULL DEFAULT 0,
    member_since    TEXT NOT NULL,
    segment         TEXT NOT NULL,              -- Leisure / Business / VIP
    marketing_optin INTEGER NOT NULL DEFAULT 0  -- 0/1 - SQLite has no BOOLEAN
);

-- ------------------------------------------------------------------ routes --
CREATE TABLE routes (
    route_id            TEXT PRIMARY KEY,       -- 'TLV-JFK'
    origin_iata         TEXT NOT NULL REFERENCES airports(iata),
    destination_iata    TEXT NOT NULL REFERENCES airports(iata),
    distance_km         INTEGER NOT NULL,
    duration_minutes    INTEGER NOT NULL,
    UNIQUE (origin_iata, destination_iata)
);

-- ----------------------------------------------------------------- flights --
CREATE TABLE flights (
    flight_id       TEXT PRIMARY KEY,           -- 'ZV101-2026-09-20'
    flight_number   TEXT NOT NULL,              -- 'ZV101'
    route_id        TEXT NOT NULL REFERENCES routes(route_id),
    tail_number     TEXT NOT NULL REFERENCES aircraft(tail_number),
    departure_time  TEXT NOT NULL,              -- 'YYYY-MM-DD HH:MM' local at origin
    arrival_time    TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN
                        ('Scheduled','Boarding','Departed','Landed','Delayed','Cancelled')),
    delay_minutes   INTEGER NOT NULL DEFAULT 0,
    gate            TEXT,
    seats_total     INTEGER NOT NULL,           -- capacity of the assigned aircraft
    seats_sold      INTEGER NOT NULL,           -- sold across ALL channels -> load factor
    base_fare       REAL NOT NULL               -- economy reference price, USD
);

-- ---------------------------------------------------------------- bookings --
CREATE TABLE bookings (
    booking_id      TEXT PRIMARY KEY,           -- PNR, e.g. 'ZKQ4TD'
    customer_id     TEXT NOT NULL REFERENCES customers(customer_id),
    agent_id        TEXT REFERENCES agents(agent_id),   -- NULL = self-service
    booking_date    TEXT NOT NULL,
    channel         TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('Confirmed','Completed','Cancelled')),
    payment_status  TEXT NOT NULL CHECK (payment_status IN ('Paid','Pending','Refunded')),
    total_amount    REAL NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'USD',
    notes           TEXT
);

-- ----------------------------------------------------------------- tickets --
-- One row = one passenger on one flight. A round trip produces two rows.
CREATE TABLE tickets (
    ticket_id       TEXT PRIMARY KEY,           -- 'TK-000001'
    booking_id      TEXT NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    flight_id       TEXT NOT NULL REFERENCES flights(flight_id),
    cabin           TEXT NOT NULL CHECK (cabin IN ('Economy','Business')),
    seat            TEXT,                       -- '12A'; NULL until assigned
    fare            REAL NOT NULL,
    baggage_count   INTEGER NOT NULL DEFAULT 0,
    checked_in      INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL CHECK (status IN ('Confirmed','Flown','Cancelled')),
    UNIQUE (flight_id, seat)                    -- a seat cannot be sold twice
);

-- ------------------------------------------------------------ interactions --
-- The service-history side of a CRM: every touch point with a customer.
CREATE TABLE interactions (
    interaction_id  TEXT PRIMARY KEY,           -- 'IN-00001'
    customer_id     TEXT NOT NULL REFERENCES customers(customer_id),
    booking_id      TEXT REFERENCES bookings(booking_id),
    agent_id        TEXT NOT NULL REFERENCES agents(agent_id),
    created_at      TEXT NOT NULL,
    channel         TEXT NOT NULL,
    topic           TEXT NOT NULL,
    subject         TEXT NOT NULL,
    priority        TEXT NOT NULL CHECK (priority IN ('Low','Medium','High')),
    status          TEXT NOT NULL CHECK (status IN ('Open','In Progress','Resolved')),
    resolved_at     TEXT
);

-- ----------------------------------------------------------------- indexes --
-- Chosen to match the filters the UI actually runs.
CREATE INDEX idx_flights_departure  ON flights(departure_time);
CREATE INDEX idx_flights_route      ON flights(route_id);
CREATE INDEX idx_flights_status     ON flights(status);
CREATE INDEX idx_tickets_flight     ON tickets(flight_id);
CREATE INDEX idx_tickets_booking    ON tickets(booking_id);
CREATE INDEX idx_bookings_customer  ON bookings(customer_id);
CREATE INDEX idx_bookings_date      ON bookings(booking_date);
CREATE INDEX idx_interactions_cust  ON interactions(customer_id);
CREATE INDEX idx_interactions_status ON interactions(status);
