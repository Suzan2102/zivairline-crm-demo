-- flights + bookings.
-- bookings is the join between customers and flights: one customer books many
-- flights, one flight carries many customers. customers is not modified here.

create table public.flights (
  id             bigint generated always as identity primary key,
  flight_number  text not null,
  origin         text not null,
  destination    text not null,
  departure_time timestamptz not null,
  arrival_time   timestamptz not null,
  constraint flights_arrival_after_departure check (arrival_time > departure_time),
  constraint flights_origin_ne_destination   check (origin <> destination)
);

create table public.bookings (
  id          bigint generated always as identity primary key,
  customer_id bigint not null references public.customers (id) on delete restrict,
  flight_id   bigint not null references public.flights (id)   on delete restrict,
  status      text not null default 'confirmed',
  booked_at   timestamptz not null default now(),
  constraint bookings_status_check check (status in ('confirmed', 'cancelled', 'pending')),
  -- a customer cannot hold two live bookings on the same flight
  constraint bookings_customer_flight_unique unique (customer_id, flight_id)
);

-- Postgres does not index FK columns automatically; without these every join
-- and every referential check is a sequential scan.
create index bookings_customer_id_idx on public.bookings (customer_id);
create index bookings_flight_id_idx   on public.bookings (flight_id);

-- Matches the existing customers table: RLS on, deny-by-default until an
-- access model is chosen.
alter table public.flights  enable row level security;
alter table public.bookings enable row level security;
