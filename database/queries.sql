-- =====================================================================
-- SMART RAILWAY MANAGEMENT SYSTEM - STANDARD & ADVANCED DBMS QUERIES
-- =====================================================================
USE smart_railway;

-- ---------------------------------------------------------------------
-- 1. SEARCH TRAINS BETWEEN TWO STATIONS ON A SPECIFIC DATE
-- Joins train, train_run, train_stop, and station tables.
-- Computes travel distance between origin and destination.
-- ---------------------------------------------------------------------
SELECT 
    r.run_id,
    t.train_number,
    t.train_name,
    t.train_type,
    r.journey_date,
    s1.station_name AS origin_station,
    s1.station_code AS origin_code,
    ts1.departure_time,
    s2.station_name AS destination_station,
    s2.station_code AS destination_code,
    ts2.arrival_time,
    (ts2.distance_from_source - ts1.distance_from_source) AS distance_km
FROM train_run r
JOIN train t ON t.train_id = r.train_id
JOIN train_stop ts1 ON ts1.train_id = t.train_id
JOIN station s1 ON s1.station_id = ts1.station_id
JOIN train_stop ts2 ON ts2.train_id = t.train_id
JOIN station s2 ON s2.station_id = ts2.station_id
WHERE r.journey_date = '2026-11-25'
  AND s1.station_code = 'SBC'
  AND s2.station_code = 'NDLS'
  AND ts1.stop_number < ts2.stop_number
ORDER BY ts1.departure_time;


-- ---------------------------------------------------------------------
-- 2. CHECK AVAILABLE SEAT COUNT PER TRAIN RUN
-- Aggregates run_seat using CASE WHEN and GROUP BY.
-- ---------------------------------------------------------------------
SELECT 
    r.run_id,
    t.train_number,
    t.train_name,
    r.journey_date,
    COUNT(rs.run_seat_id) AS total_seats,
    SUM(CASE WHEN rs.seat_status = 'Available' THEN 1 ELSE 0 END) AS available_seats,
    SUM(CASE WHEN rs.seat_status = 'Booked' THEN 1 ELSE 0 END) AS booked_seats
FROM train_run r
JOIN train t ON t.train_id = r.train_id
LEFT JOIN run_seat rs ON rs.run_id = r.run_id
WHERE r.journey_date >= CURRENT_DATE
GROUP BY r.run_id, t.train_number, t.train_name, r.journey_date
ORDER BY r.journey_date, t.train_number;


-- ---------------------------------------------------------------------
-- 3. GET SEAT INVENTORY DETAILS FOR A SPECIFIC RUN
-- Shows seat number, coach, coach type, berth, and status.
-- ---------------------------------------------------------------------
SELECT 
    rs.run_seat_id,
    c.coach_number,
    c.coach_type,
    s.seat_number,
    s.berth_type,
    rs.seat_status
FROM run_seat rs
JOIN seat s ON s.seat_id = rs.seat_id
JOIN coach c ON c.coach_id = s.coach_id
WHERE rs.run_id = 60
ORDER BY c.coach_number, s.seat_number;


-- ---------------------------------------------------------------------
-- 4. VIEW ALL STOPS AND TIMETABLE FOR A GIVEN TRAIN (e.g. 12627)
-- ---------------------------------------------------------------------
SELECT 
    ts.stop_number,
    s.station_code,
    s.station_name,
    s.city,
    s.state,
    ts.arrival_time,
    ts.departure_time,
    ts.distance_from_source AS km_from_start
FROM train_stop ts
JOIN train t ON t.train_id = ts.train_id
JOIN station s ON s.station_id = ts.station_id
WHERE t.train_number = '12627'
ORDER BY ts.stop_number;


-- ---------------------------------------------------------------------
-- 5. PASSENGER BOOKING SUMMARY WITH TICKET DETAILS
-- Multi-table JOIN linking booking, passenger, train_run, train, seats.
-- ---------------------------------------------------------------------
SELECT 
    b.booking_id,
    b.booking_date,
    b.booking_status,
    p.passenger_name,
    p.email,
    p.phone_number,
    t.train_number,
    t.train_name,
    r.journey_date,
    b.total_fare,
    GROUP_CONCAT(CONCAT(c.coach_number, '-', s.seat_number, ' (', s.berth_type, ')') ORDER BY s.seat_number SEPARATOR ', ') AS booked_seats
FROM booking b
JOIN passenger p ON p.passenger_id = b.passenger_id
JOIN train_run r ON r.run_id = b.run_id
JOIN train t ON t.train_id = r.train_id
JOIN booking_seat bs ON bs.booking_id = b.booking_id
JOIN seat s ON s.seat_id = bs.seat_id
JOIN coach c ON c.coach_id = s.coach_id
GROUP BY b.booking_id, b.booking_date, b.booking_status, p.passenger_name, p.email, p.phone_number, t.train_number, t.train_name, r.journey_date, b.total_fare
ORDER BY b.booking_id DESC;


-- ---------------------------------------------------------------------
-- 6. TOTAL REVENUE AND BOOKINGS PER TRAIN
-- Uses aggregate functions SUM, COUNT, and GROUP BY.
-- ---------------------------------------------------------------------
SELECT 
    t.train_number,
    t.train_name,
    COUNT(DISTINCT b.booking_id) AS total_bookings,
    COUNT(bs.booking_seat_id) AS total_passengers_booked,
    COALESCE(SUM(CASE WHEN b.booking_status = 'Confirmed' THEN b.total_fare ELSE 0 END), 0) AS confirmed_revenue,
    COALESCE(SUM(CASE WHEN b.booking_status = 'Cancelled' THEN b.total_fare ELSE 0 END), 0) AS cancelled_revenue
FROM train t
LEFT JOIN train_run r ON r.train_id = t.train_id
LEFT JOIN booking b ON b.run_id = r.run_id
LEFT JOIN booking_seat bs ON bs.booking_id = b.booking_id
GROUP BY t.train_id, t.train_number, t.train_name
ORDER BY confirmed_revenue DESC;


-- ---------------------------------------------------------------------
-- 7. OCCUPANCY RATE PERCENTAGE PER TRAIN RUN
-- Demonstrates nested calculations and percentages.
-- ---------------------------------------------------------------------
SELECT 
    r.run_id,
    t.train_number,
    t.train_name,
    r.journey_date,
    COUNT(rs.run_seat_id) AS capacity,
    SUM(CASE WHEN rs.seat_status = 'Booked' THEN 1 ELSE 0 END) AS occupied_seats,
    ROUND(
        (SUM(CASE WHEN rs.seat_status = 'Booked' THEN 1 ELSE 0 END) * 100.0) / NULLIF(COUNT(rs.run_seat_id), 0),
        2
    ) AS occupancy_percentage
FROM train_run r
JOIN train t ON t.train_id = r.train_id
JOIN run_seat rs ON rs.run_id = r.run_id
GROUP BY r.run_id, t.train_number, t.train_name, r.journey_date
ORDER BY r.journey_date;


-- ---------------------------------------------------------------------
-- 8. PASSENGERS WITH MULTIPLE BOOKINGS (SUBQUERY / HAVING)
-- Identifies frequent travellers.
-- ---------------------------------------------------------------------
SELECT 
    p.passenger_id,
    p.passenger_name,
    p.email,
    p.phone_number,
    COUNT(b.booking_id) AS total_bookings,
    SUM(b.total_fare) AS total_spent
FROM passenger p
JOIN booking b ON b.passenger_id = p.passenger_id
GROUP BY p.passenger_id, p.passenger_name, p.email, p.phone_number
HAVING COUNT(b.booking_id) >= 1
ORDER BY total_bookings DESC, total_spent DESC;


-- ---------------------------------------------------------------------
-- 9. STATIONS SERVED BY MOST TRAINS (POPULAR JUNCTIONS)
-- ---------------------------------------------------------------------
SELECT 
    s.station_code,
    s.station_name,
    s.city,
    s.state,
    COUNT(DISTINCT ts.train_id) AS active_train_routes
FROM station s
JOIN train_stop ts ON ts.station_id = s.station_id
GROUP BY s.station_id, s.station_code, s.station_name, s.city, s.state
ORDER BY active_train_routes DESC, s.station_name
LIMIT 10;


-- ---------------------------------------------------------------------
-- 10. BERTH TYPE PREFERENCE AND DISTRIBUTION
-- ---------------------------------------------------------------------
SELECT 
    s.berth_type,
    COUNT(s.seat_id) AS total_seats_configured,
    COUNT(bs.booking_seat_id) AS total_times_booked
FROM seat s
LEFT JOIN booking_seat bs ON bs.seat_id = s.seat_id
GROUP BY s.berth_type
ORDER BY total_times_booked DESC;
