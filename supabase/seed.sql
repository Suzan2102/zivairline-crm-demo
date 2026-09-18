-- Synthetic customer data for development/testing.
-- All addresses use RFC 2606 reserved domains so test data can never
-- reach a real inbox.

insert into public.customers (name, email) values
  ('יוסי כהן',         'yossi.cohen@example.com'),
  ('מיכל לוי',          'michal.levi@example.co.il'),
  ('אבי מזרחי',        'avi.mizrahi@example.com'),
  ('נועה פרידמן',      'noa.friedman@example.org'),
  ('דניאל שפירא',      'daniel.shapira@example.com'),
  ('תמר בן-דוד',       'tamar.bendavid@example.co.il'),
  ('אורי גולן',         'uri.golan@example.net'),
  ('שירה אברהם',       'shira.avraham@example.com'),
  ('רונן ביטון',        'ronen.biton@example.co.il'),
  ('יעל רוזנברג',      'yael.rosenberg@example.com'),
  ('איתי דהן',          'itay.dahan@example.org'),
  ('מאיה קליין',        'maya.klein@example.com'),
  ('עומר שרון',         'omer.sharon@example.co.il'),
  ('ליאת אזולאי',      'liat.azoulay@example.com'),
  ('גיא ברקוביץ',      'guy.berkovitz@example.net'),
  ('הדר מלכה',         'hadar.malka@example.com'),
  ('אסף נחום',         'assaf.nachum@example.co.il'),
  ('רותם סגל',          'rotem.segal@example.org'),
  ('ניר אוחיון',        'nir.ohayon@example.com'),
  ('שני פלד',           'shani.peled@example.co.il'),
  ('עידו הרשקוביץ',   'ido.hershkovitz@example.com'),
  ('דנה ויצמן',        'dana.weizman@example.net'),
  ('אלון גרינברג',    'alon.greenberg@example.com'),
  ('כרמית סויסה',     'carmit.suissa@example.co.il'),
  ('בן ארצי',           'ben.artzi@example.org'),
  ('ספיר טל',           'sapir.tal@example.com'),
  ('יונתן אשכנזי',    'yonatan.ashkenazi@example.co.il'),
  ('אורית חדד',        'orit.haddad@example.com'),
  -- leads captured by phone, email not yet collected
  ('משה אלבז',         null),
  ('ורד שטרן',          null);
-- Synthetic flights + bookings.
-- All times are UTC. Routes are TLV-centric to match the CRM's domain.

insert into public.flights (flight_number, origin, destination, departure_time, arrival_time) values
  ('LY315', 'TLV', 'LHR', '2026-10-02 06:20+00', '2026-10-02 11:05+00'),
  ('LY316', 'LHR', 'TLV', '2026-10-09 13:40+00', '2026-10-09 18:15+00'),
  ('LY001', 'TLV', 'JFK', '2026-10-05 21:00+00', '2026-10-06 05:30+00'),
  ('LY002', 'JFK', 'TLV', '2026-10-15 22:10+00', '2026-10-16 06:40+00'),
  ('IZ621', 'TLV', 'CDG', '2026-10-11 05:45+00', '2026-10-11 10:00+00'),
  ('IZ622', 'CDG', 'TLV', '2026-10-18 11:30+00', '2026-10-18 15:40+00'),
  ('6H431', 'TLV', 'ATH', '2026-10-21 07:15+00', '2026-10-21 09:05+00'),
  ('6H432', 'ATH', 'TLV', '2026-10-25 10:00+00', '2026-10-25 11:45+00'),
  ('LY391', 'TLV', 'FCO', '2026-11-03 08:30+00', '2026-11-03 11:10+00'),
  ('LY392', 'FCO', 'TLV', '2026-11-10 12:25+00', '2026-11-10 14:55+00'),
  ('IZ553', 'TLV', 'BCN', '2026-11-07 06:00+00', '2026-11-07 09:40+00'),
  ('LY381', 'TLV', 'AMS', '2026-11-14 09:10+00', '2026-11-14 13:05+00'),
  ('6H701', 'TLV', 'LCA', '2026-11-19 14:00+00', '2026-11-19 14:55+00'),
  ('LY083', 'TLV', 'BKK', '2026-11-22 20:30+00', '2026-11-23 08:15+00'),
  ('LY051', 'TLV', 'DXB', '2026-12-01 10:45+00', '2026-12-01 13:50+00'),
  ('LY052', 'DXB', 'TLV', '2026-12-08 15:20+00', '2026-12-08 18:30+00');

-- Bookings are sampled across the customer x flight grid rather than
-- hand-written, so the data stays valid whatever the actual id values are.
-- setseed makes the sample reproducible on a fresh db reset.
select setseed(0.42);

insert into public.bookings (customer_id, flight_id, status, booked_at)
select
  c.id,
  f.id,
  case
    when random() < 0.08 then 'cancelled'
    when random() < 0.20 then 'pending'
    else 'confirmed'
  end,
  now() - (random() * interval '90 days')
from public.customers c
cross join public.flights f
where random() < 0.15
on conflict (customer_id, flight_id) do nothing;
