/* ═══════════════════════════════════════════════════
   Railway Reservation System — Frontend Logic
   ═══════════════════════════════════════════════════ */

const API = "http://localhost:8000";

// ── State ──────────────────────────────────────────
let token = localStorage.getItem("token");
let currentUser = null;

// ── DOM Helpers ────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ── Toast ──────────────────────────────────────────
function toast(msg, type = "info") {
    const el = $("#toast");
    el.textContent = msg;
    el.className = "toast " + type;
    setTimeout(() => el.classList.add("show"), 10);
    setTimeout(() => el.classList.remove("show"), 3500);
}

// ── API Helper ─────────────────────────────────────
async function api(path, opts = {}) {
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(API + path, { ...opts, headers });
    const data = res.status !== 204 ? await res.json() : null;

    if (!res.ok) {
        const msg = data?.detail || "Something went wrong";
        throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    return data;
}

// ══════════════════════════════════════════════════
//  STATION AUTOCOMPLETE
// ══════════════════════════════════════════════════
async function loadStations() {
    try {
        const stations = await api("/trains/stations");
        const datalist = $("#stationList");
        datalist.innerHTML = stations
            .map((s) => `<option value="${s}">`)
            .join("");
    } catch {
        // silently ignore — autocomplete is a nice-to-have
    }
}

// ══════════════════════════════════════════════════
//  AUTH — MODALS
// ══════════════════════════════════════════════════
function showModal(id) {
    document.getElementById(id).classList.add("show");
}

function hideModal(id) {
    document.getElementById(id).classList.remove("show");
}

// Close modals on backdrop click
document.addEventListener("click", (e) => {
    if (e.target.classList.contains("modal")) {
        e.target.classList.remove("show");
    }
});

// ── Register ───────────────────────────────────────
async function handleRegister(e) {
    e.preventDefault();
    const username = $("#regUsername").value.trim();
    const email = $("#regEmail").value.trim();
    const password = $("#regPassword").value;

    try {
        await api("/auth/register", {
            method: "POST",
            body: JSON.stringify({ username, email, password }),
        });
        toast("Account created! Please login.", "success");
        hideModal("registerModal");
        showModal("loginModal");
        e.target.reset();
    } catch (err) {
        toast(err.message, "error");
    }
}

// ── Login ──────────────────────────────────────────
async function handleLogin(e) {
    e.preventDefault();
    const email = $("#loginEmail").value.trim();
    const password = $("#loginPassword").value;

    try {
        const data = await api("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password }),
        });
        token = data.access_token;
        localStorage.setItem("token", token);
        hideModal("loginModal");
        e.target.reset();
        toast("Welcome back!", "success");
        await loadProfile();
    } catch (err) {
        toast(err.message, "error");
    }
}

// ── Logout ─────────────────────────────────────────
function logout() {
    token = null;
    currentUser = null;
    localStorage.removeItem("token");
    updateAuthUI();
    navigateTo("search");
    toast("Logged out", "info");
}

// ── Load Profile ───────────────────────────────────
async function loadProfile() {
    if (!token) {
        updateAuthUI();
        return;
    }
    try {
        currentUser = await api("/auth/me");
        updateAuthUI();
    } catch {
        token = null;
        currentUser = null;
        localStorage.removeItem("token");
        updateAuthUI();
    }
}

// ── Update UI based on auth ───────────────────────
function updateAuthUI() {
    const loggedIn = !!currentUser;
    const isAdmin = currentUser?.role === "admin";

    // Greeting
    const greet = $("#userGreeting");
    greet.textContent = loggedIn ? `Hi, ${currentUser.username}` : "";
    greet.style.display = loggedIn ? "" : "none";

    // Auth buttons
    $("#loginBtn").style.display = loggedIn ? "none" : "";
    $("#registerBtn").style.display = loggedIn ? "none" : "";
    $("#logoutBtn").style.display = loggedIn ? "" : "none";

    // Auth-only nav links
    $$(".auth-only").forEach(
        (el) => (el.style.display = loggedIn ? "" : "none")
    );

    // Admin-only nav links
    $$(".admin-only").forEach(
        (el) => (el.style.display = isAdmin ? "" : "none")
    );
}

// ══════════════════════════════════════════════════
//  NAVIGATION
// ══════════════════════════════════════════════════
function navigateTo(pageName) {
    // Hide all pages, show selected
    $$(".page").forEach((p) => p.classList.remove("active"));
    const target = document.getElementById("page-" + pageName);
    if (target) target.classList.add("active");

    // Update active nav link
    $$(".nav-link").forEach((l) => l.classList.remove("active"));
    const activeLink = $(`.nav-link[data-page="${pageName}"]`);
    if (activeLink) activeLink.classList.add("active");

    // Lazy-load data for pages
    if (pageName === "bookings" && currentUser) loadBookings();
    if (pageName === "admin" && currentUser) loadAdminTrains();
    if (pageName === "search") loadAllTrains();
}

// Wire nav links
$$(".nav-link").forEach((link) => {
    link.addEventListener("click", (e) => {
        e.preventDefault();
        const page = link.dataset.page;
        if ((page === "bookings" || page === "admin") && !currentUser) {
            showModal("loginModal");
            return;
        }
        navigateTo(page);
    });
});

// ══════════════════════════════════════════════════
//  TRAINS — SEARCH & LIST
// ══════════════════════════════════════════════════
function formatTime(dt) {
    if (!dt) return "--:--";
    const d = new Date(dt);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function trainCardHTML(train) {
    const avail = train.available_seats;
    const badgeClass = avail > 0 ? "seats-available" : "seats-full";
    const bookBtn =
        avail > 0
            ? `<button class="btn btn-primary btn-sm" onclick="bookSeat(${train.id})">Book Seat</button>`
            : `<button class="btn btn-sm" disabled>Full</button>`;

    return `
    <div class="train-card">
        <div class="train-card-header">
            <div>
                <span class="train-number">#${train.train_number}</span>
                <div class="train-name">${train.train_name}</div>
            </div>
        </div>
        <div class="train-route">
            <div class="station">
                <div class="station-name">${train.source}</div>
                <div class="station-time">${formatTime(train.departure_time)}</div>
            </div>
            <span class="route-arrow">→</span>
            <div class="station">
                <div class="station-name">${train.destination}</div>
                <div class="station-time">${formatTime(train.arrival_time)}</div>
            </div>
        </div>
        <div class="train-footer">
            <span class="seats-badge ${badgeClass}">${avail} / ${train.total_seats} seats</span>
            ${bookBtn}
        </div>
    </div>`;
}

// ── Search ─────────────────────────────────────────
async function searchTrains() {
    const source = $("#searchSource").value.trim();
    const destination = $("#searchDest").value.trim();

    if (!source && !destination) {
        toast("Enter a source or destination", "error");
        return;
    }
    try {
        const params = new URLSearchParams();
        if (source) params.set("source", source);
        if (destination) params.set("destination", destination);

        const trains = await api(`/trains/search?${params}`);
        const grid = $("#trainResults");
        if (trains.length === 0) {
            grid.innerHTML = `<div class="empty-state"><span class="empty-icon">🔍</span><p>No trains found for this route.</p></div>`;
        } else {
            grid.innerHTML = trains.map((t) => trainCardHTML(t)).join("");
        }
    } catch (err) {
        toast(err.message, "error");
    }
}

// ── Swap Stations ──────────────────────────────────
function swapStations() {
    const src = $("#searchSource");
    const dest = $("#searchDest");
    [src.value, dest.value] = [dest.value, src.value];
}

// ── Load all trains ────────────────────────────────
async function loadAllTrains() {
    try {
        const trains = await api("/trains");
        const grid = $("#allTrains");
        if (trains.length === 0) {
            grid.innerHTML = `<div class="empty-state"><span class="empty-icon">🚂</span><p>No trains available yet.</p></div>`;
        } else {
            grid.innerHTML = trains.map((t) => trainCardHTML(t)).join("");
        }
    } catch (err) {
        toast(err.message, "error");
    }
}

// ══════════════════════════════════════════════════
//  BOOKING
// ══════════════════════════════════════════════════
async function bookSeat(trainId) {
    if (!currentUser) {
        showModal("loginModal");
        return;
    }
    try {
        const booking = await api("/bookings", {
            method: "POST",
            body: JSON.stringify({ train_id: trainId }),
        });
        toast(
            `Booked! Seat #${booking.seat_number} confirmed.`,
            "success"
        );
        loadAllTrains(); // refresh availability
    } catch (err) {
        toast(err.message, "error");
    }
}

// ── My Bookings ────────────────────────────────────
async function loadBookings() {
    try {
        const bookings = await api("/bookings/my");
        const list = $("#bookingsList");
        const empty = $("#noBookings");

        if (bookings.length === 0) {
            list.innerHTML = "";
            empty.style.display = "";
            return;
        }

        empty.style.display = "none";
        list.innerHTML = bookings
            .map((b) => {
                const isCancelled = b.status === "cancelled";
                const statusClass = isCancelled
                    ? "status-cancelled"
                    : "status-confirmed";
                return `
            <div class="booking-card ${isCancelled ? "cancelled" : ""}">
                <div class="booking-meta">
                    <span class="booking-id">Booking #${b.id}</span>
                    <span class="status-badge ${statusClass}">${b.status}</span>
                </div>
                <div class="train-name">${b.train_name} <span class="train-number">#${b.train_number}</span></div>
                <div class="booking-seat">Seat No: <strong>${b.seat_number}</strong></div>
                <div class="booking-date">Booked: ${new Date(b.booked_at).toLocaleString()}</div>
                ${
                    !isCancelled
                        ? `<div class="booking-actions"><button class="btn btn-danger btn-sm" onclick="cancelBooking(${b.id})">Cancel</button></div>`
                        : ""
                }
            </div>`;
            })
            .join("");
    } catch (err) {
        toast(err.message, "error");
    }
}

async function cancelBooking(id) {
    if (!confirm("Cancel this booking?")) return;
    try {
        await api(`/bookings/${id}`, { method: "DELETE" });
        toast("Booking cancelled", "info");
        loadBookings();
    } catch (err) {
        toast(err.message, "error");
    }
}

// ══════════════════════════════════════════════════
//  ADMIN
// ══════════════════════════════════════════════════
async function handleAddTrain(e) {
    e.preventDefault();
    const body = {
        train_number: $("#trainNumber").value.trim(),
        train_name: $("#trainName").value.trim(),
        source: $("#trainSource").value.trim(),
        destination: $("#trainDest").value.trim(),
        total_seats: parseInt($("#trainSeats").value, 10),
        departure_time: $("#trainDepart").value || undefined,
        arrival_time: $("#trainArrive").value || undefined,
    };

    try {
        await api("/admin/trains", {
            method: "POST",
            body: JSON.stringify(body),
        });
        toast("Train added!", "success");
        e.target.reset();
        loadAdminTrains();
        loadStations(); // refresh station autocomplete
    } catch (err) {
        toast(err.message, "error");
    }
}

async function loadAdminTrains() {
    try {
        const trains = await api("/trains");
        const list = $("#adminTrainList");
        if (trains.length === 0) {
            list.innerHTML = `<div class="empty-state"><span class="empty-icon">🛤️</span><p>No trains added yet.</p></div>`;
            return;
        }
        list.innerHTML = trains
            .map(
                (t) => `
            <div class="train-card">
                <div class="train-card-header">
                    <div>
                        <span class="train-number">#${t.train_number}</span>
                        <div class="train-name">${t.train_name}</div>
                    </div>
                    <div class="admin-actions">
                        <button class="btn btn-danger btn-sm" onclick="deleteTrain(${t.id})">Delete</button>
                    </div>
                </div>
                <div class="train-route">
                    <div class="station">
                        <div class="station-name">${t.source}</div>
                        <div class="station-time">${formatTime(t.departure_time)}</div>
                    </div>
                    <span class="route-arrow">→</span>
                    <div class="station">
                        <div class="station-name">${t.destination}</div>
                        <div class="station-time">${formatTime(t.arrival_time)}</div>
                    </div>
                </div>
                <div class="train-footer">
                    <span class="seats-badge seats-available">${t.available_seats} / ${t.total_seats} seats</span>
                </div>
            </div>`
            )
            .join("");
    } catch (err) {
        toast(err.message, "error");
    }
}

async function deleteTrain(id) {
    if (!confirm("Delete this train permanently?")) return;
    try {
        await api(`/admin/trains/${id}`, { method: "DELETE" });
        toast("Train deleted", "info");
        loadAdminTrains();
        loadStations(); // refresh station autocomplete
    } catch (err) {
        toast(err.message, "error");
    }
}

// ══════════════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════════════
(async function init() {
    await loadProfile();
    await loadStations();
    navigateTo("search");
})();
