const { url, key } = window.SUPABASE_CONFIG;
const db = window.supabase.createClient(url, key);

const el = (id) => document.getElementById(id);
const state = { view: "customers", rows: [], search: "" };

/* ---------- helpers ---------- */

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

const fmtDate = (iso) =>
  iso ? new Date(iso).toLocaleString("he-IL", { dateStyle: "short", timeStyle: "short" }) : "—";

const STATUS_HE = { confirmed: "מאושר", pending: "ממתין", cancelled: "בוטל" };

function showAlert(html, bad = false) {
  const a = el("alert");
  a.innerHTML = html;
  a.classList.toggle("bad", bad);
  a.hidden = false;
}

function formMsg(text, ok = false) {
  const m = el("login-msg");
  m.textContent = text;
  m.classList.toggle("ok", ok);
  m.hidden = !text;
}

/* ---------- auth ---------- */

async function signIn(e) {
  e.preventDefault();
  formMsg("");
  el("login-btn").disabled = true;

  const { error } = await db.auth.signInWithPassword({
    email: el("email").value.trim(),
    password: el("password").value
  });

  el("login-btn").disabled = false;

  if (error) {
    // Supabase returns the same message for a wrong password and an unknown
    // address, on purpose: it stops the form being used to discover which
    // addresses have accounts.
    formMsg(
      error.message === "Invalid login credentials"
        ? "אימייל או סיסמה שגויים"
        : error.message
    );
  }
  // On success onAuthStateChange takes over.
}

async function signUp() {
  formMsg("");
  const email = el("email").value.trim();
  const password = el("password").value;

  if (!email || password.length < 6) {
    formMsg("נדרש אימייל וסיסמה באורך 6 תווים לפחות");
    return;
  }

  const { data, error } = await db.auth.signUp({ email, password });

  if (error) {
    formMsg(error.message);
  } else if (data.session) {
    formMsg("המשתמש נוצר, מתחבר…", true);
  } else {
    formMsg("המשתמש נוצר. יש לאשר את הכתובת במייל לפני הכניסה.", true);
  }
}

async function signOut() {
  await db.auth.signOut();
}

/* ---------- views ---------- */

const VIEWS = {
  customers: {
    from: "customers",
    select: "id, name, email",
    order: { column: "id" },
    head: ["#", "שם", "אימייל"],
    search: (r, q) =>
      (r.name || "").toLowerCase().includes(q) || (r.email || "").toLowerCase().includes(q),
    row: (r) => `
      <td class="num">${r.id}</td>
      <td>${esc(r.name)}</td>
      <td class="ltr">${r.email ? esc(r.email) : '<span class="dim">—</span>'}</td>`
  },

  flights: {
    from: "flights",
    select: "id, flight_number, origin, destination, departure_time, arrival_time",
    order: { column: "departure_time" },
    head: ["טיסה", "מסלול", "המראה", "נחיתה"],
    search: (r, q) =>
      `${r.flight_number} ${r.origin} ${r.destination}`.toLowerCase().includes(q),
    row: (r) => `
      <td class="ltr">${esc(r.flight_number)}</td>
      <td class="ltr">${esc(r.origin)} ← ${esc(r.destination)}</td>
      <td>${fmtDate(r.departure_time)}</td>
      <td>${fmtDate(r.arrival_time)}</td>`
  },

  // The nested selects resolve through the foreign keys on bookings.
  bookings: {
    from: "bookings",
    select:
      "id, status, booked_at, customers(name), flights(flight_number, origin, destination)",
    order: { column: "booked_at", ascending: false },
    head: ["#", "לקוח", "טיסה", "מסלול", "סטטוס", "הוזמן"],
    search: (r, q) =>
      `${r.customers?.name ?? ""} ${r.flights?.flight_number ?? ""}`.toLowerCase().includes(q),
    row: (r) => `
      <td class="num">${r.id}</td>
      <td>${esc(r.customers?.name)}</td>
      <td class="ltr">${esc(r.flights?.flight_number)}</td>
      <td class="ltr">${esc(r.flights?.origin)} ← ${esc(r.flights?.destination)}</td>
      <td><span class="pill ${esc(r.status)}">${STATUS_HE[r.status] ?? esc(r.status)}</span></td>
      <td class="dim">${fmtDate(r.booked_at)}</td>`
  }
};

/* ---------- data ---------- */

function render() {
  const view = VIEWS[state.view];
  const q = state.search.trim().toLowerCase();
  const rows = q ? state.rows.filter((r) => view.search(r, q)) : state.rows;

  el("thead").innerHTML = `<tr>${view.head.map((h) => `<th>${h}</th>`).join("")}</tr>`;
  el("tbody").innerHTML = rows.map((r) => `<tr>${view.row(r)}</tr>`).join("");
  el("count").textContent = rows.length ? `${rows.length} רשומות` : "";

  const empty = el("empty");
  empty.hidden = rows.length > 0;
  if (!rows.length) empty.textContent = q ? "אין תוצאות לחיפוש" : "אין נתונים להצגה";
}

async function load() {
  const view = VIEWS[state.view];
  el("tbody").innerHTML = "";
  el("empty").hidden = true;

  const { data, error } = await db
    .from(view.from)
    .select(view.select)
    .order(view.order.column, { ascending: view.order.ascending ?? true });

  if (error) {
    el("conn").textContent = "שגיאה";
    el("conn").className = "badge bad";
    showAlert(`<b>שגיאה בשליפה מ־${view.from}:</b> ${esc(error.message)}`, true);
    return;
  }

  state.rows = data;
  render();
}

async function loadStats() {
  const count = (table) => db.from(table).select("*", { count: "exact", head: true });

  const [c, f, b, ok] = await Promise.all([
    count("customers"),
    count("flights"),
    count("bookings"),
    db.from("bookings").select("*", { count: "exact", head: true }).eq("status", "confirmed")
  ]);

  el("stat-customers").textContent = c.count ?? "—";
  el("stat-flights").textContent   = f.count ?? "—";
  el("stat-bookings").textContent  = b.count ?? "—";
  el("stat-confirmed").textContent = ok.count ?? "—";

  const badge = el("conn");

  if (c.error) {
    badge.textContent = "שגיאת הרשאה";
    badge.className = "badge bad";
    showAlert(
      `<b>החיבור תקין אך הקריאה נדחתה:</b> ${esc(c.error.message)}<br>
       המשתמש מחובר אך ה־policy אינו מתיר לו קריאה.`,
      true
    );
  } else {
    badge.textContent = "מחובר";
    badge.className = "badge ok";
    el("alert").hidden = true;
  }
}

/* ---------- session routing ---------- */

function showApp(session) {
  el("gate").hidden = true;
  el("app").hidden = false;
  el("user-email").textContent = session.user.email;
  loadStats();
  load();
}

function showGate() {
  el("app").hidden = true;
  el("gate").hidden = false;
  el("login-form").reset();
  formMsg("");
}

db.auth.onAuthStateChange((_event, session) => {
  session ? showApp(session) : showGate();
});

/* ---------- events ---------- */

el("login-form").addEventListener("submit", signIn);
el("signup-btn").addEventListener("click", signUp);
el("logout-btn").addEventListener("click", signOut);

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("is-active"));
    tab.classList.add("is-active");
    state.view = tab.dataset.view;
    state.search = "";
    el("search").value = "";
    load();
  });
});

el("search").addEventListener("input", (e) => {
  state.search = e.target.value;
  render();
});

/* Decide which screen to show once, on load. onAuthStateChange handles the
   rest, including the token refresh that restores a session after a reload. */
db.auth.getSession().then(({ data }) => (data.session ? showApp(data.session) : showGate()));
