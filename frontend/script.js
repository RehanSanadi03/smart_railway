const byId = (id) => document.getElementById(id);
const notice = byId("notice");
let chosenRun = null;
let chosenSeats = new Set();

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `Request failed (${response.status}).`);
  return payload;
}

function showNotice(message, kind = "info") {
  notice.textContent = message;
  notice.className = `notice ${kind}`;
  notice.hidden = false;
  notice.scrollIntoView({ behavior: "smooth", block: "center" });
}

function clearNotice() {
  notice.hidden = true;
  notice.textContent = "";
}

function addStationOption(select, station) {
  const option = document.createElement("option");
  option.value = station.station_code;
  option.textContent = `${station.station_name} · ${station.station_code} — ${station.city}`;
  select.append(option);
}

async function loadStations() {
  try {
    const stations = await api("/api/stations");
    stations.forEach((station) => {
      addStationOption(byId("origin"), station);
      addStationOption(byId("destination"), station);
    });
  } catch (error) {
    showNotice(`Could not load stations: ${error.message}`, "error");
  }
}

function timeText(value) {
  if (!value) return "Time not listed";
  return String(value).slice(0, 5);
}

function renderTrain(train) {
  const card = document.createElement("article");
  card.className = "train-card";
  const summary = document.createElement("div");
  summary.className = "train-summary";
  const identity = document.createElement("div");
  identity.innerHTML = "";
  const number = document.createElement("span");
  number.className = "train-number";
  number.textContent = `${train.train_number} · ${train.train_type}`;
  const name = document.createElement("h3");
  name.textContent = train.train_name;
  identity.append(number, name);

  const route = document.createElement("div");
  route.className = "route-times";
  const origin = document.createElement("div");
  origin.innerHTML = `<span class="muted">DEPARTURE</span>`;
  const originTime = document.createElement("strong");
  originTime.textContent = timeText(train.departure_time);
  const originName = document.createElement("span");
  originName.textContent = `${train.origin_name} (${train.origin_code})`;
  origin.append(originTime, originName);
  const arrow = document.createElement("span");
  arrow.className = "route-arrow";
  arrow.textContent = "→";
  const destination = document.createElement("div");
  destination.innerHTML = `<span class="muted">ARRIVAL</span>`;
  const destinationTime = document.createElement("strong");
  destinationTime.textContent = timeText(train.arrival_time);
  const destinationName = document.createElement("span");
  destinationName.textContent = `${train.destination_name} (${train.destination_code})`;
  destination.append(destinationTime, destinationName);
  route.append(origin, arrow, destination);

  const action = document.createElement("div");
  action.className = "train-action";
  const availability = document.createElement("span");
  const inventoryMissing = train.available_seats === null;
  const count = Number(train.available_seats || 0);
  availability.className = inventoryMissing || count ? "available" : "sold-out";
  availability.textContent = inventoryMissing
    ? "Schedule listed · inventory not loaded"
    : count ? `${count} seats available` : "No seats available";
  const button = document.createElement("button");
  button.className = "secondary";
  button.type = "button";
  button.textContent = "Select seats";
  button.disabled = inventoryMissing || !count;
  button.addEventListener("click", () => openSeats(train));
  action.append(availability, button);
  summary.append(identity, route, action);
  card.append(summary);
  return card;
}

byId("search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  clearNotice();
  const form = new FormData(event.currentTarget);
  const params = new URLSearchParams({
    origin: form.get("origin"), destination: form.get("destination"), date: form.get("date"),
  });
  const resultsSection = byId("results-section");
  const results = byId("results");
  results.replaceChildren();
  resultsSection.hidden = false;
  byId("result-count").textContent = "Searching…";
  try {
    const trains = await api(`/api/trains/search?${params}`);
    byId("result-count").textContent = `${trains.length} ${trains.length === 1 ? "service" : "services"}`;
    if (!trains.length) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "No trains match this route and date. Try another journey.";
      results.append(empty);
    } else {
      trains.forEach((train) => results.append(renderTrain(train)));
    }
  } catch (error) {
    byId("result-count").textContent = "";
    showNotice(error.message, "error");
  }
});

const CLASS_METADATA = {
  "AC First Class": { code: "1A", short: "1st Tier AC (1A)", order: 1 },
  "AC 2 Tier": { code: "2A", short: "2nd Tier AC (2A)", order: 2 },
  "AC 3 Tier": { code: "3A", short: "3rd Tier AC (3A)", order: 3 },
  "Executive Chair Car": { code: "EC", short: "Executive (EC)", order: 4 },
  "AC Chair Car": { code: "CC", short: "Chair Car (CC)", order: 5 },
  "Sleeper": { code: "SL", short: "Sleeper (SL)", order: 6 },
};

async function openSeats(train) {
  clearNotice();
  chosenRun = train;
  chosenSeats = new Set();
  byId("dialog-title").textContent = `${train.train_number} · ${train.train_name}`;
  byId("seat-list").replaceChildren();
  byId("class-filter-bar").replaceChildren();
  byId("selected-summary").textContent = "Select one or more available seats.";

  try {
    const seats = await api(`/api/runs/${train.run_id}/seats`);

    // Group seats by coach
    const coaches = new Map();
    const classCounts = new Map();
    let totalAvail = 0;

    seats.forEach((seat) => {
      const coachKey = seat.coach_number;
      if (!coaches.has(coachKey)) {
        coaches.set(coachKey, {
          coach_number: seat.coach_number,
          coach_type: seat.coach_type,
          seats: [],
          availableCount: 0,
        });
      }
      const coach = coaches.get(coachKey);
      coach.seats.push(seat);

      const isAvail = seat.seat_status === "Available";
      if (isAvail) {
        coach.availableCount++;
        totalAvail++;
        classCounts.set(seat.coach_type, (classCounts.get(seat.coach_type) || 0) + 1);
      }
    });

    let currentClassFilter = "ALL";

    function renderSeatsForFilter(filterClass) {
      const container = byId("seat-list");
      container.replaceChildren();

      coaches.forEach((coach) => {
        if (filterClass !== "ALL" && coach.coach_type !== filterClass) {
          return;
        }

        const section = document.createElement("div");
        section.className = "coach-section";

        const meta = CLASS_METADATA[coach.coach_type] || { code: coach.coach_type, short: coach.coach_type };

        const header = document.createElement("div");
        header.className = "coach-header";
        header.innerHTML = `
          <span>Coach ${coach.coach_number} · ${meta.short}</span>
          <span class="coach-class-tag">${coach.availableCount} seats available</span>
        `;

        const grid = document.createElement("div");
        grid.className = "coach-seats-grid";

        coach.seats.forEach((seat) => {
          const button = document.createElement("button");
          button.type = "button";
          const isSelected = chosenSeats.has(seat.seat_id);
          button.className = `seat ${seat.seat_status === "Available" ? "free" : "occupied"} ${isSelected ? "selected" : ""}`;
          button.disabled = seat.seat_status !== "Available";
          button.innerHTML = `
            <span class="seat-num">${seat.coach_number}-${seat.seat_number}</span>
            <span class="seat-berth">${seat.berth_type}</span>
          `;
          button.title = `Coach ${seat.coach_number}, Seat ${seat.seat_number} (${meta.code}, ${seat.berth_type}) · ${seat.seat_status}`;
          button.setAttribute("aria-label", `${seat.coach_number}, seat ${seat.seat_number}, ${meta.code}, ${seat.berth_type}, ${seat.seat_status}`);

          if (!button.disabled) {
            button.addEventListener("click", () => {
              if (chosenSeats.has(seat.seat_id)) {
                chosenSeats.delete(seat.seat_id);
                button.classList.remove("selected");
              } else {
                chosenSeats.add(seat.seat_id);
                button.classList.add("selected");
              }
              byId("selected-summary").textContent = chosenSeats.size
                ? `${chosenSeats.size} seat${chosenSeats.size === 1 ? "" : "s"} selected. Fare is calculated from route distance.`
                : "Select one or more available seats.";
            });
          }
          grid.append(button);
        });

        section.append(header, grid);
        container.append(section);
      });
    }

    // Render class filter tabs
    const filterBar = byId("class-filter-bar");
    
    // "All Classes" button
    const allTab = document.createElement("button");
    allTab.type = "button";
    allTab.className = "class-tab active";
    allTab.innerHTML = `All Classes <span class="class-badge-count">${totalAvail}</span>`;
    allTab.addEventListener("click", () => {
      currentClassFilter = "ALL";
      filterBar.querySelectorAll(".class-tab").forEach((t) => t.classList.remove("active"));
      allTab.classList.add("active");
      renderSeatsForFilter("ALL");
    });
    filterBar.append(allTab);

    // Sort distinct classes by order
    const presentClasses = [...classCounts.keys()].sort((a, b) => {
      const ordA = CLASS_METADATA[a]?.order || 99;
      const ordB = CLASS_METADATA[b]?.order || 99;
      return ordA - ordB;
    });

    presentClasses.forEach((cType) => {
      const meta = CLASS_METADATA[cType] || { code: cType, short: cType };
      const avail = classCounts.get(cType) || 0;
      const tab = document.createElement("button");
      tab.type = "button";
      tab.className = "class-tab";
      tab.innerHTML = `${meta.short} <span class="class-badge-count">${avail}</span>`;
      tab.addEventListener("click", () => {
        currentClassFilter = cType;
        filterBar.querySelectorAll(".class-tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        renderSeatsForFilter(cType);
      });
      filterBar.append(tab);
    });

    // Initial render: show all coaches
    renderSeatsForFilter("ALL");

    byId("booking-dialog").showModal();
  } catch (error) {
    showNotice(`Could not load seats: ${error.message}`, "error");
  }
}

byId("close-dialog").addEventListener("click", () => byId("booking-dialog").close());
byId("booking-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  clearNotice();
  const form = byId("booking-form");
  if (!chosenSeats.size) {
    byId("selected-summary").textContent = "Choose at least one available seat to continue.";
    return;
  }
  const formData = new FormData(form);
  const passenger = Object.fromEntries(formData.entries());
  if (passenger.age === "") delete passenger.age;
  try {
    const booking = await api("/api/bookings", {
      method: "POST",
      body: JSON.stringify({
        passenger,
        run_id: chosenRun.run_id,
        origin: chosenRun.origin_code,
        destination: chosenRun.destination_code,
        seat_ids: [...chosenSeats],
      }),
    });
    byId("booking-dialog").close();
    form.reset();
    byId("booking-id").value = booking.booking_id;
    showNotice(`Booking confirmed! Booking ID: ${booking.booking_id} · Total fare: ₹${booking.total_fare}. Save your Booking ID for your records.`, "success");
    byId("search-form").requestSubmit();
    loadBookingDetails(booking.booking_id);
    loadRecentBookings();
  } catch (error) {
    showNotice(error.message, "error");
  }
});

async function loadRecentBookings() {
  const container = byId("recent-bookings-list");
  if (!container) return;
  try {
    const bookings = await api("/api/bookings");
    container.replaceChildren();
    if (!bookings.length) {
      container.innerHTML = `<p class="muted">No bookings recorded yet in the database.</p>`;
      return;
    }
    bookings.forEach((b) => {
      const card = document.createElement("div");
      card.className = "booking-item-card";

      const badgeClass = b.booking_status === "Confirmed" ? "confirmed" : "cancelled";
      const isConfirmed = b.booking_status === "Confirmed";

      const info = document.createElement("div");
      info.className = "booking-item-info";
      info.innerHTML = `
        <div class="booking-item-title">
          <span>Booking #${b.booking_id} · ${b.train_number} ${b.train_name}</span>
          <span class="ticket-badge ${badgeClass}">${b.booking_status}</span>
        </div>
        <div class="muted">Passenger: <strong>${b.passenger_name}</strong> · Journey Date: <strong>${b.journey_date}</strong> · Seats: <strong>${b.seats || "N/A"}</strong></div>
        <div class="muted">Fare: <strong>₹${b.total_fare}</strong> · Booked: ${b.booking_date ? String(b.booking_date).replace("T", " ").slice(0, 19) : "N/A"}</div>
      `;

      const actions = document.createElement("div");
      actions.className = "booking-item-actions";

      const viewBtn = document.createElement("button");
      viewBtn.type = "button";
      viewBtn.className = "btn-small-secondary";
      viewBtn.textContent = "View Ticket";
      viewBtn.addEventListener("click", () => {
        byId("booking-id").value = b.booking_id;
        loadBookingDetails(b.booking_id);
      });
      actions.append(viewBtn);

      if (isConfirmed) {
        const cancelBtn = document.createElement("button");
        cancelBtn.type = "button";
        cancelBtn.className = "btn-small-danger";
        cancelBtn.textContent = "Cancel";
        cancelBtn.addEventListener("click", async () => {
          if (!confirm(`Cancel Booking #${b.booking_id} for ${b.passenger_name}?`)) return;
          try {
            await api(`/api/bookings/${b.booking_id}/cancel`, { method: "POST", body: "{}" });
            showNotice(`Booking #${b.booking_id} was successfully cancelled.`, "success");
            loadBookingDetails(b.booking_id);
            loadRecentBookings();
            byId("search-form").requestSubmit();
          } catch (err) {
            showNotice(err.message, "error");
          }
        });
        actions.append(cancelBtn);
      }

      card.append(info, actions);
      container.append(card);
    });
  } catch (err) {
    container.innerHTML = `<p class="muted">Could not load bookings: ${err.message}</p>`;
  }
}

byId("refresh-bookings-btn")?.addEventListener("click", () => {
  loadRecentBookings();
});

async function loadBookingDetails(bookingId) {
  try {
    const b = await api(`/api/bookings/${bookingId}`);
    const box = byId("booking-details-box");
    const seatsStr = (b.seats || [])
      .map((s) => `${s.coach_number}-${s.seat_number} (${s.coach_type}, ${s.berth_type})`)
      .join(", ") || "None";
    const badgeClass = b.booking_status === "Confirmed" ? "confirmed" : "cancelled";
    box.innerHTML = `
      <div class="ticket-card-header">
        <span>Booking #${b.booking_id} · ${b.train_number} ${b.train_name} (${b.train_type})</span>
        <span class="ticket-badge ${badgeClass}">${b.booking_status}</span>
      </div>
      <div><strong>Passenger:</strong> ${b.passenger_name} ${b.email ? `· ${b.email}` : ""} ${b.phone_number ? `· ${b.phone_number}` : ""}</div>
      <div><strong>Journey Date:</strong> ${b.journey_date}</div>
      <div><strong>Seats:</strong> ${seatsStr}</div>
      <div><strong>Total Fare:</strong> ₹${b.total_fare}</div>
      <div><small class="muted">Booked on: ${b.booking_date || "N/A"}</small></div>
    `;
    box.hidden = false;
    box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    byId("booking-details-box").hidden = true;
    showNotice(`Could not fetch ticket details: ${error.message}`, "error");
  }
}

byId("view-booking-btn").addEventListener("click", () => {
  clearNotice();
  const bookingId = byId("booking-id").value;
  if (!bookingId) {
    showNotice("Please enter a Booking ID to view ticket details.", "error");
    return;
  }
  loadBookingDetails(bookingId);
});

byId("cancel-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  clearNotice();
  const bookingId = byId("booking-id").value;
  try {
    await api(`/api/bookings/${bookingId}/cancel`, { method: "POST", body: "{}" });
    showNotice(`Booking #${bookingId} has been successfully cancelled.`, "success");
    loadBookingDetails(bookingId);
    loadRecentBookings();
    byId("search-form").requestSubmit();
  } catch (error) {
    showNotice(error.message, "error");
  }
});

document.querySelectorAll(".route-pill").forEach((pill) => {
  pill.addEventListener("click", () => {
    byId("origin").value = pill.dataset.origin;
    byId("destination").value = pill.dataset.destination;
    byId("search-form").requestSubmit();
  });
});

const today = new Date();
const todayStr = new Date(today.getTime() - today.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const dateInput = byId("search-form").elements.date;
dateInput.min = todayStr;
if (!dateInput.value) {
  dateInput.value = todayStr;
}
loadStations();
loadRecentBookings();
