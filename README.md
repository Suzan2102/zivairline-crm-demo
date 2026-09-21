# ZivAirline CRM

A flights CRM built on **Supabase** (Postgres, Auth, Storage) with a plain
HTML/CSS/JS frontend in Hebrew (RTL). Admins see the whole airline; customers
sign in and see only their own bookings, flights and passport.

> Teaching demo. All customer data in `supabase/seed.sql` is synthetic, and every
> email address uses an RFC 2606 reserved domain, so it can never reach a real inbox.

---

## What it does

| Role | Sees |
|------|------|
| **admin** | Every customer, flight and booking; a departures board with a booking count per flight; every uploaded passport |
| **customer** | Their own customer row, their own bookings, and only the flights those bookings point at; a card to upload their own passport |

The dashboard is built around a departures board: monospace flight rows, a live
clock, and status colours that always carry a text label (confirmed / pending /
cancelled).

---

## Quick start

The frontend is static files, so there is no build step.

```bash
# serve the web/ folder with any static server, for example:
npx serve web
# or
python -m http.server 8000 --directory web
```

Then open the printed address and sign in with a Supabase Auth user.

`web/config.js` holds the project URL and the **publishable** key. That key is
designed to be public — it grants only what the RLS policies allow. Never put
the `service_role` or secret key in the frontend; keep it in `.env` (ignored by git).

### Database

The schema lives in `supabase/migrations/` and the demo data in `supabase/seed.sql`.
With the Supabase CLI linked to the project:

```bash
supabase db push       # apply the migrations
supabase db reset      # local only: rebuild and reseed
```

### Making a user an admin

The role is read from `app_metadata.role`, which only the auth server can write
(`user_metadata` is user-editable and never drives authorization). Set it from
the Supabase dashboard or with the service key:

```sql
update auth.users
set raw_app_meta_data = raw_app_meta_data || '{"role": "admin"}'
where email = 'admin@example.com';
```

A customer account is linked to its CRM row through `customers.user_id`:

```sql
update public.customers set user_id = '<auth user uuid>' where id = 1;
```

---

## Project layout

```
.
├── supabase/
│   ├── config.toml
│   ├── seed.sql                 # 30 customers, 16 flights, ~66 bookings
│   └── migrations/
│       ├── …_create_customers_table.sql
│       ├── …_create_flights_and_bookings.sql
│       ├── …_add_authenticated_read_policies.sql
│       ├── …_add_role_based_access.sql
│       └── …_add_passport_storage.sql
└── web/
    ├── index.html               # login gate, dashboard, inline SVG illustration
    ├── styles.css               # light sky theme
    ├── app.js                   # auth, data loading, board, passport upload
    └── config.js                # Supabase URL + publishable key
```

---

## The data model

```
customers ──< bookings >── flights
    │
 auth.users (via user_id)
```

| Table | Holds |
|-------|-------|
| `customers` | `id`, `name`, `email`, and a nullable `user_id` → `auth.users` |
| `flights` | Flight number, origin, destination, departure and arrival times |
| `bookings` | The many-to-many join: one customer on one flight, with `status` (`confirmed` / `pending` / `cancelled`) |

Constraints worth knowing:

- A flight must arrive after it departs, and cannot fly to its own origin.
- A customer cannot hold two bookings on the same flight.
- Both foreign-key columns on `bookings` are indexed — Postgres does not do that automatically.

---

## Security model

Access is enforced by Row Level Security in the database, not by the frontend.
The UI renders an admin panel or a customer view from the role claim, but that is
presentation only: a tampered claim still returns nothing, because the policies decide.

- **anon** holds no grant at all and receives nothing.
- **admin** (`private.is_admin()`) reads every row.
- **customer** reads rows tied to `private.current_customer_id()`.
- Helper functions live in a `private` schema the Data API does not expose.
  `current_customer_id()` is `SECURITY DEFINER` so the bookings and flights policies
  can look up `customers` without recursing into its policy; it can only ever return
  the caller's own id.

### Passport storage

- Bucket `passports` is **private**: no public URL, 5 MB limit, JPEG / PNG / PDF only.
- Files are stored as `<auth user id>/passport.<ext>`; the first path segment is the ownership check.
- Owners read, upload, replace and delete their own file. Admins can read every file
  but cannot upload, so staff cannot plant a document under a customer's identity.
- Reads go through 60-second signed URLs.

---

## History

This project started as a Streamlit + SQLite prototype (dashboard, flights and
customers modules with a synthetic data generator). That version is preserved on the
[`backup/streamlit-phase4`](https://github.com/Suzan2102/zivairline-crm-demo/tree/backup/streamlit-phase4)
branch.
