# Smart Railway Management System

A full-stack Railway Management DBMS application built with a Python Flask backend, MySQL database, and responsive frontend UI.

---

## Features

- **Dynamic Two-Way Route Search**: Search trains across major routes and intermediate stops in both directions (e.g., Bengaluru ↔ Delhi, Chennai ↔ Mysuru, Mumbai ↔ Delhi, Delhi ↔ Bhopal, Belagavi ↔ Bengaluru, Pune ↔ Mumbai).
- **Interactive Seat Map**: Live coach seat inventory retrieved directly from `coach`, `seat`, and `run_seat` tables with berth types (Lower, Middle, Upper, Side Lower, Side Upper, Chair Car).
- **Transactional Booking**: Concurrency-safe reservations with InnoDB `FOR UPDATE` row locking, passenger creation/reuse, ticket pricing calculated from `train_stop.distance_from_source`, and inventory updates.
- **Ticket Details & PNR Lookup**: View confirmed tickets, seat allocations, coach details, passenger info, and booking timestamps.
- **Reservation Cancellation**: Cancel bookings with immediate seat restoration back to `Available` status in `run_seat`.
- **DBMS Query Suite**: Complete reference SQL suite in `database/queries.sql` showcasing JOINs, aggregations, occupancy analytics, and revenue reports.

---

## Database Architecture

The system uses 10 normalized relational tables in MySQL (`smart_railway`):

1. `station`: Station codes, names, cities, and states.
2. `train`: Train numbers, names, and service types (Rajdhani, Shatabdi, Superfast, Express).
3. `train_stop`: Timetable stops with arrival/departure times and cumulative route distance.
4. `coach`: Coaches per train (`S1`, `S2`, `C1`, `B1`, etc.).
5. `seat`: Seat numbers (1–72) with berth assignments.
6. `train_run`: Scheduled train runs by date.
7. `run_seat`: Real-time seat inventory and status (`Available`, `Booked`).
8. `passenger`: Passenger profiles with email, phone, and age.
9. `booking`: Reservation records with status and total fare.
10. `booking_seat`: Individual seats and fares linked to each booking.

---

## Quick Start

### 1. Configuration (`.env`)
Ensure `.env` contains your MySQL settings and fare rate:
```ini
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=smart_railway
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_CONNECT_TIMEOUT=10
RAIL_FARE_PER_KM=0.75
```

### 2. Run the Application
In PowerShell:
```powershell
.venv\Scripts\python.exe backend\app.py
```
Open your browser at `http://127.0.0.1:5000`.

### 3. Run Automated System Tests
To verify all routes, seat loading, bookings, ticket lookup, and cancellations:
```powershell
.venv\Scripts\python.exe test_system.py
```

---

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/stations` | List all stations for dropdowns |
| `GET` | `/api/trains/search?origin=X&destination=Y&date=YYYY-MM-DD` | Search available trains & seats |
| `GET` | `/api/runs/<run_id>/seats` | Get seat map & availability for a run |
| `POST` | `/api/bookings` | Book selected seats (transactional) |
| `GET` | `/api/bookings/<booking_id>` | View complete ticket details |
| `POST` | `/api/bookings/<booking_id>/cancel` | Cancel booking & release seats |
