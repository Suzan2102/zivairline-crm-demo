-- Access model: signed-in staff read everything; nobody writes through the API.
--
-- anon gets no grant and no policy, so an unauthenticated visitor holding the
-- publishable key sees nothing at all.

grant usage on schema public to authenticated;
grant select on public.customers, public.flights, public.bookings to authenticated;

-- Defensive: make sure anon holds nothing, even if granted elsewhere earlier.
revoke all on public.customers, public.flights, public.bookings from anon;

-- Anonymous sign-ins (if ever enabled) carry the `authenticated` Postgres role,
-- so `to authenticated` alone would let them in. The is_anonymous claim is set
-- by the auth server and is not user-editable, unlike user_metadata.
-- auth.jwt() is wrapped in a subquery so it evaluates once per statement
-- instead of once per row.
create policy customers_staff_read on public.customers
  for select to authenticated
  using ( coalesce(((select auth.jwt()) ->> 'is_anonymous')::boolean, false) = false );

create policy flights_staff_read on public.flights
  for select to authenticated
  using ( coalesce(((select auth.jwt()) ->> 'is_anonymous')::boolean, false) = false );

create policy bookings_staff_read on public.bookings
  for select to authenticated
  using ( coalesce(((select auth.jwt()) ->> 'is_anonymous')::boolean, false) = false );
