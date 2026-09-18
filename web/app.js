const { url, key } = window.SUPABASE_CONFIG;
const db = window.supabase.createClient(url, key);

const el = (id) => document.getElementById(id);
const state = { view: "customers", rows: [], search: "", isAdmin: false };

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

/* The role is read from app_metadata, which only the auth server can write.
   This drives which screen renders — it is not a security boundary. The real
   enforcement is in the RLS policies, so a user who tampers with this in
   devtools still gets nothing back from the database. */
const isAdmin = (session) => session?.user?.app_metadata?.role === "admin";

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
    formMsg(
      error.message === "Invalid login credentials"
        ? "אימייל או סיסמה שגויים"
        : error.message
    );
  }
}

const signOut = () => db.auth.signOut();

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

  bookings: {
    from: "bookings",
    select:
      "id, status, booked_at, customers(name), flights(flight_number, origin, destination, departure_time)",
    order: { column: "booked_at", ascending: false },
    head: ["#", "לקוח", "טיסה", "מסלול", "המראה", "סטטוס"],
    search: (r, q) =>
      `${r.customers?.name ?? ""} ${r.flights?.flight_number ?? ""}`.toLowerCase().includes(q),
    row: (r) => `
      <td class="num">${r.id}</td>
      <td>${esc(r.customers?.name)}</td>
      <td class="ltr">${esc(r.flights?.flight_number)}</td>
      <td class="ltr">${esc(r.flights?.origin)} ← ${esc(r.flights?.destination)}</td>
      <td>${fmtDate(r.flights?.departure_time)}</td>
      <td><span class="pill ${esc(r.status)}">${STATUS_HE[r.status] ?? esc(r.status)}</span></td>`
  },

  passports: {
    custom: true,
    head: ["#", "לקוח", "אימייל", "דרכון"],
    search: (r, q) => (r.name || "").toLowerCase().includes(q),
    row: (r) => `
      <td class="num">${r.id}</td>
      <td>${esc(r.name)}</td>
      <td class="ltr">${esc(r.email)}</td>
      <td>${
        r.path
          ? `<button class="btn-inline" data-path="${esc(r.path)}">צפייה</button>`
          : '<span class="dim">לא הועלה</span>'
      }</td>`
  },

  // Customer screen: same rows, without the redundant own-name column.
  myBookings: {
    from: "bookings",
    select:
      "id, status, booked_at, flights(flight_number, origin, destination, departure_time, arrival_time)",
    order: { column: "booked_at", ascending: false },
    head: ["טיסה", "מסלול", "המראה", "נחיתה", "סטטוס"],
    search: () => true,
    row: (r) => `
      <td class="ltr">${esc(r.flights?.flight_number)}</td>
      <td class="ltr">${esc(r.flights?.origin)} ← ${esc(r.flights?.destination)}</td>
      <td>${fmtDate(r.flights?.departure_time)}</td>
      <td>${fmtDate(r.flights?.arrival_time)}</td>
      <td><span class="pill ${esc(r.status)}">${STATUS_HE[r.status] ?? esc(r.status)}</span></td>`
  }
};

/* ---------- data ---------- */

function render() {
  const view = VIEWS[state.view];
  const q = state.search.trim().toLowerCase();
  const rows = q ? state.rows.filter((r) => view.search(r, q)) : state.rows;

  el("thead").innerHTML = `<tr>${view.head.map((h) => `<th>${h}</th>`).join("")}</tr>`;
  el("tbody").innerHTML = rows.map((r) => `<tr>${view.row(r)}</tr>`).join("");
  if (state.isAdmin) el("count").textContent = rows.length ? `${rows.length} רשומות` : "";

  const empty = el("empty");
  empty.hidden = rows.length > 0;
  if (!rows.length) empty.textContent = q ? "אין תוצאות לחיפוש" : "אין נתונים להצגה";
}

async function load() {
  const view = VIEWS[state.view];
  el("tbody").innerHTML = "";
  el("empty").hidden = true;

  if (view.custom) {
    state.rows = await loadPassportTable();
    el("conn").textContent = "מחובר";
    el("conn").className = "badge ok";
    render();
    return;
  }

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

  el("conn").textContent = "מחובר";
  el("conn").className = "badge ok";
  state.rows = data;
  render();
}

async function loadStats() {
  const count = (t) => db.from(t).select("*", { count: "exact", head: true });

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
}


/* ---------- passport storage ---------- */

const BUCKET = "passports";

/* The first path segment is the owner check enforced by the storage policies,
   so it has to be the uid. A filename the user picks never touches it. */
const folderFor = (session) => session.user.id;

async function findPassport(uid) {
  const { data, error } = await db.storage.from(BUCKET).list(uid, { limit: 1 });
  if (error || !data?.length) return null;
  return `${uid}/${data[0].name}`;
}

/* The bucket is private, so there is no permanent URL to hand out. A signed
   URL is minted per view and expires in 60s. */
async function signedUrl(path) {
  const { data, error } = await db.storage.from(BUCKET).createSignedUrl(path, 60);
  return error ? null : data.signedUrl;
}

function passportMsg(text, ok = false) {
  const m = el("passport-msg");
  m.textContent = text;
  m.classList.toggle("ok", ok);
  m.hidden = !text;
}

async function refreshPassport(session) {
  const path = await findPassport(folderFor(session));
  const status = el("passport-status");
  const view = el("passport-view");

  if (!path) {
    status.textContent = "טרם הועלה";
    status.classList.remove("has");
    view.hidden = true;
    el("passport-upload").textContent = "העלאה";
    return;
  }

  status.textContent = "הועלה";
  status.classList.add("has");
  el("passport-upload").textContent = "החלפה";

  const url = await signedUrl(path);
  if (url) {
    view.href = url;
    view.hidden = false;
  }
}

async function uploadPassport(session) {
  const file = el("passport-file").files[0];
  if (!file) return;

  const btn = el("passport-upload");
  btn.disabled = true;
  passportMsg("");

  const uid = folderFor(session);
  const ext = (file.name.split(".").pop() || "bin").toLowerCase();

  // Remove whatever is there first, otherwise a jpg replacing a png leaves
  // two files in the folder and the list order decides which one wins.
  const existing = await findPassport(uid);
  if (existing) await db.storage.from(BUCKET).remove([existing]);

  const { error } = await db.storage
    .from(BUCKET)
    .upload(`${uid}/passport.${ext}`, file, { upsert: true, contentType: file.type });

  btn.disabled = false;

  if (error) {
    // The bucket caps size and mime type, so these are the usual rejections.
    passportMsg(
      /exceeded|too large/i.test(error.message) ? "הקובץ גדול מ־5MB"
      : /mime|type/i.test(error.message)        ? "סוג קובץ לא נתמך"
      : error.message
    );
    return;
  }

  el("passport-file").value = "";
  passportMsg("הדרכון הועלה", true);
  refreshPassport(session);
}

/* Admin view: one folder listing per linked customer. Fine at this scale;
   with thousands of customers this wants a passport_path column instead. */
async function loadPassportTable() {
  const { data: customers, error } = await db
    .from("customers")
    .select("id, name, email, user_id")
    .not("user_id", "is", null)
    .order("id");

  if (error) {
    showAlert(`<b>שגיאה:</b> ${esc(error.message)}`, true);
    return [];
  }

  return Promise.all(
    customers.map(async (c) => ({ ...c, path: await findPassport(c.user_id) }))
  );
}

async function openPassport(e) {
  const path = e.target.dataset.path;
  if (!path) return;
  const url = await signedUrl(path);
  if (url) window.open(url, "_blank", "noopener");
}

/* ---------- session routing ---------- */

function showApp(session) {
  formMsg("");
  el("gate").hidden = true;
  el("app").hidden = false;
  el("user-email").textContent = session.user.email;

  state.isAdmin = isAdmin(session);

  const tag = el("role-tag");
  tag.textContent = state.isAdmin ? "מנהל" : "לקוח";
  tag.classList.toggle("customer", !state.isAdmin);

  el("admin-panel").hidden = !state.isAdmin;
  el("customer-panel").hidden = state.isAdmin;

  if (state.isAdmin) {
    state.view = "customers";
    loadStats();
  } else {
    state.view = "myBookings";
    el("customer-greeting").textContent =
      "מוצגות ההזמנות והמסמכים המשויכים לחשבון שלך בלבד.";
    refreshPassport(session);
    el("passport-file").onchange = (e) => {
      el("passport-upload").disabled = !e.target.files.length;
    };
    el("passport-upload").onclick = () => uploadPassport(session);
  }

  load();
}

function showGate() {
  el("app").hidden = true;
  el("gate").hidden = false;
  el("login-form").reset();
  formMsg("");
}

db.auth.onAuthStateChange((_event, session) =>
  session ? showApp(session) : showGate()
);

/* ---------- events ---------- */

el("login-form").addEventListener("submit", signIn);
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

el("tbody").addEventListener("click", (e) => {
  if (e.target.matches("[data-path]")) openPassport(e);
});

el("search").addEventListener("input", (e) => {
  state.search = e.target.value;
  render();
});

db.auth.getSession().then(({ data }) =>
  data.session ? showApp(data.session) : showGate()
);
