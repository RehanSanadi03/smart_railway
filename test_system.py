import sys
sys.path.insert(0, "backend")
from app import create_app

client = create_app().test_client()

test_routes = [
    ("SBC", "NDLS", "Bengaluru to New Delhi"),
    ("NDLS", "SBC", "New Delhi to Bengaluru (Return)"),
    ("MAS", "MYS", "Chennai to Mysuru"),
    ("MYS", "MAS", "Mysuru to Chennai (Return)"),
    ("MMCT", "NDLS", "Mumbai to New Delhi"),
    ("NDLS", "MMCT", "New Delhi to Mumbai (Return)"),
    ("BGM", "SBC", "Belagavi to Bengaluru"),
    ("PUNE", "MMCT", "Pune to Mumbai"),
]

print("=== 1. VERIFYING TWO-WAY ROUTE SEARCHES ===")
for origin, dest, label in test_routes:
    res = client.get(f"/api/trains/search?origin={origin}&destination={dest}&date=2026-11-25")
    trains = res.get_json()
    assert res.status_code == 200, f"Search failed: {res.status_code}"
    assert len(trains) > 0, f"No trains found for {origin} -> {dest}"
    t = trains[0]
    avail = t.get("available_seats")
    assert avail is not None and avail > 0, f"No available seats for {origin} -> {dest}"
    print(f"PASS: {label} [{origin} -> {dest}]")
    print(f"      Train: #{t['train_number']} {t['train_name']} ({t['train_type']})")
    print(f"      Distance: {t['distance_km']} km | Available Seats: {int(avail)}")

print("\n=== 2. VERIFYING SEAT INVENTORY ENDPOINT ===")
run_id = trains[0]["run_id"]
res = client.get(f"/api/runs/{run_id}/seats")
seats = res.get_json()
assert res.status_code == 200 and len(seats) > 0
available_seats = [s for s in seats if s["seat_status"] == "Available"]
print(f"PASS: Loaded {len(seats)} seats for Run #{run_id} ({len(available_seats)} available)")

print("\n=== 3. VERIFYING TRANSACTIONAL BOOKING ===")
selected_seat = available_seats[0]
book_payload = {
    "passenger": {
        "passenger_name": "Course Evaluator",
        "email": "evaluator@dbms-project.edu",
        "phone_number": "9988776655",
        "age": 28
    },
    "run_id": run_id,
    "origin": "PUNE",
    "destination": "MMCT",
    "seat_ids": [selected_seat["seat_id"]]
}
res = client.post("/api/bookings", json=book_payload)
assert res.status_code == 201, f"Booking failed: {res.get_json()}"
booking = res.get_json()
booking_id = booking["booking_id"]
print(f"PASS: Booking confirmed! ID: #{booking_id}, Total Fare: Rs {booking['total_fare']}")

print("\n=== 4. VERIFYING TICKET DETAILS LOOKUP ===")
res = client.get(f"/api/bookings/{booking_id}")
ticket = res.get_json()
assert res.status_code == 200
print(f"PASS: Ticket retrieved! Passenger: {ticket['passenger_name']}, Train: {ticket['train_name']}, Status: {ticket['booking_status']}")
print(f"      Assigned Seat: Coach {ticket['seats'][0]['coach_number']}, Seat {ticket['seats'][0]['seat_number']} ({ticket['seats'][0]['berth_type']})")

print("\n=== 5. VERIFYING BOOKING CANCELLATION & SEAT RELEASE ===")
res = client.post(f"/api/bookings/{booking_id}/cancel", json={})
assert res.status_code == 200 and res.get_json()["booking_status"] == "Cancelled"
print(f"PASS: Booking #{booking_id} cancelled.")

res = client.get(f"/api/runs/{run_id}/seats")
seat_status = [s["seat_status"] for s in res.get_json() if s["seat_id"] == selected_seat["seat_id"]][0]
assert seat_status == "Available", f"Expected Available, got {seat_status}"
print(f"PASS: Seat #{selected_seat['seat_id']} safely released back to 'Available' status.")

print("\n=== ALL DATABASE AND APPLICATION VERIFICATIONS PASSED SUCCESSFULLY! ===")
