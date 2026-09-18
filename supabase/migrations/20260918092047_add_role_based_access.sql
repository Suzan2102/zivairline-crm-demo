-- Two roles:
--   admin    -> every row in every table
--   customer -> only their own customer row, their own bookings, and the
--               flights those bookings point at
--
-- Additive only: customers keeps its existing columns and all 30 rows.

alter table public.customers
  add column user_id uuid references auth.users (id) on delete set null;

create unique index customers_user_id_key on public.customers (user_id)
  where user_id is not null;

-- Helpers live in a schema the Data API does not expose, so neither anon nor
-- authenticated can call them directly over REST.
create schema if not exists private;
revoke all on schema private from anon, authenticated;

-- The role lives in app_metadata, which only the auth server can write.
-- user_metadata is user-editable and must never drive authorization.
create or replace function private.is_admin()
returns boolean
language sql
stable
security invoker
set search_path = ''
as $$
  select coalesce(
    ((select auth.jwt()) -> 'app_metadata' ->> 'role') = 'admin',
    false
  );
$$;

-- SECURITY DEFINER is required here: the bookings and flights policies below
-- look up public.customers, and doing that as the caller would re-enter the
-- customers policy and recurse. The function can only ever return the calling
-- user's own id, so it leaks nothing.
create or replace function private.current_customer_id()
returns bigint
language sql
stable
security definer
set search_path = ''
as $$
  select id
  from public.customers
  where user_id = (select auth.uid())
  limit 1;
$$;

revoke execute on function private.is_admin(), private.current_customer_id()
  from public, anon;
grant usage on schema private to authenticated;
grant execute on function private.is_admin(), private.current_customer_id()
  to authenticated;

-- Replace the blanket staff-read policies from the previous migration.
drop policy customers_staff_read on public.customers;
drop policy flights_staff_read   on public.flights;
drop policy bookings_staff_read  on public.bookings;

create policy customers_read on public.customers
  for select to authenticated
  using (
    (select private.is_admin())
    or id = (select private.current_customer_id())
  );

create policy bookings_read on public.bookings
  for select to authenticated
  using (
    (select private.is_admin())
    or customer_id = (select private.current_customer_id())
  );

-- A customer sees a flight only if they hold a booking on it.
create policy flights_read on public.flights
  for select to authenticated
  using (
    (select private.is_admin())
    or exists (
      select 1 from public.bookings b
      where b.flight_id = flights.id
        and b.customer_id = (select private.current_customer_id())
    )
  );
