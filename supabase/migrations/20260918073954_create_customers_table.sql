-- Customers table for the CRM.
-- id/name/email only, per spec.

create table public.customers (
  id    bigint generated always as identity primary key,
  name  text not null,
  email text
);

-- RLS is enabled with no policies: deny-by-default for anon/authenticated.
-- Access is only possible via service_role until an access model is defined.
alter table public.customers enable row level security;
