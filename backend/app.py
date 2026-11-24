"""Flask API for the existing Smart Railway MySQL schema."""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from mysql.connector import Error as MySQLError
from dotenv import load_dotenv

from db import get_connection, inspect_schema


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
load_dotenv(FRONTEND_DIR.parent / ".env", override=False)


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds()) % (24 * 60 * 60)
        hours, seconds = divmod(seconds, 60 * 60)
        minutes, seconds = divmod(seconds, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _body_object():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError("Send a JSON object in the request body.")
    return body


def _positive_int(value, field):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ApiError(f"{field} must be a positive integer.") from None
    if number <= 0:
        raise ApiError(f"{field} must be a positive integer.")
    return number


def _rows(cursor):
    return cursor.fetchall()


def create_app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/style.css")
    def style():
        return send_from_directory(FRONTEND_DIR, "style.css")

    @app.get("/script.js")
    def script():
        return send_from_directory(FRONTEND_DIR, "script.js")

    @app.errorhandler(ApiError)
    def api_error(error):
        return jsonify({"error": str(error)}), error.status

    @app.errorhandler(MySQLError)
    def database_error(error):
        app.logger.exception("Database operation failed")
        return jsonify({"error": "The database operation failed."}), 500

    @app.get("/api/stations")
    def stations():
        connection = get_connection()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT station_id, station_code, station_name, city, state "
                "FROM station ORDER BY station_name"
            )
            return jsonify(_json_value(_rows(cursor)))
        finally:
            connection.close()

    @app.get("/api/trains/search")
    def search_trains():
        origin = request.args.get("origin", "").strip().upper()
        destination = request.args.get("destination", "").strip().upper()
        travel_date = request.args.get("date", "").strip()
        if not origin or not destination or not travel_date:
            raise ApiError("origin, destination, and date are required.")
        if origin == destination:
            raise ApiError("Origin and destination must be different.")
        try:
            date.fromisoformat(travel_date)
        except ValueError:
            raise ApiError("date must use YYYY-MM-DD format.") from None

        connection = get_connection()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """SELECT r.run_id, t.train_id, t.train_number, t.train_name,
                          t.train_type, r.journey_date,
                          s1.station_code AS origin_code,
                          s1.station_name AS origin_name,
                          ts1.departure_time,
                          s2.station_code AS destination_code,
                          s2.station_name AS destination_name,
                          ts2.arrival_time,
                          (ts2.distance_from_source - ts1.distance_from_source)
                              AS distance_km,
                          CASE WHEN COUNT(rs.run_seat_id) = 0 THEN NULL
                               ELSE SUM(CASE WHEN rs.seat_status = 'Available'
                                             THEN 1 ELSE 0 END)
                          END AS available_seats
                   FROM train_run r
                   JOIN train t ON t.train_id = r.train_id
                   JOIN train_stop ts1 ON ts1.train_id = t.train_id
                   JOIN station s1 ON s1.station_id = ts1.station_id
                   JOIN train_stop ts2 ON ts2.train_id = t.train_id
                   JOIN station s2 ON s2.station_id = ts2.station_id
                   LEFT JOIN run_seat rs ON rs.run_id = r.run_id
                   WHERE r.journey_date = %s
                     AND s1.station_code = %s AND s2.station_code = %s
                     AND ts1.stop_number < ts2.stop_number
                   GROUP BY r.run_id, t.train_id, t.train_number, t.train_name,
                            t.train_type, r.journey_date, s1.station_code,
                            s1.station_name, ts1.departure_time,
                            s2.station_code, s2.station_name, ts2.arrival_time,
                            ts1.distance_from_source, ts2.distance_from_source
                   ORDER BY ts1.departure_time, t.train_number""",
                (travel_date, origin, destination),
            )
            return jsonify(_json_value(_rows(cursor)))
        finally:
            connection.close()

    @app.get("/api/runs/<int:run_id>/seats")
    def run_seats(run_id):
        connection = get_connection()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """SELECT rs.run_seat_id, rs.seat_id, rs.seat_status,
                          s.seat_number, s.berth_type, c.coach_number,
                          c.coach_type
                   FROM run_seat rs
                   JOIN seat s ON s.seat_id = rs.seat_id
                   JOIN coach c ON c.coach_id = s.coach_id
                   WHERE rs.run_id = %s
                   ORDER BY c.coach_number, s.seat_number""",
                (run_id,),
            )
            return jsonify(_json_value(_rows(cursor)))
        finally:
            connection.close()

    @app.post("/api/passengers")
    def create_passenger():
        body = _body_object()
        name = str(body.get("passenger_name", "")).strip()
        if not name:
            raise ApiError("passenger_name is required.")
        age = body.get("age")
        if age not in (None, ""):
            try:
                age = int(age)
            except (TypeError, ValueError):
                raise ApiError("age must be between 5 and 120.") from None
            if age < 5 or age > 120:
                raise ApiError("age must be between 5 and 120.")
        else:
            age = None
        birth_date = body.get("date_of_birth") or None
        if birth_date:
            try:
                date.fromisoformat(birth_date)
            except (TypeError, ValueError):
                raise ApiError("date_of_birth must use YYYY-MM-DD format.") from None

        email = str(body.get("email", "")).strip() or None
        phone = str(body.get("phone_number", "")).strip() or None

        connection = get_connection()
        try:
            cursor = connection.cursor(dictionary=True)
            if email or phone:
                cursor.execute(
                    """SELECT passenger_id, passenger_name FROM passenger
                       WHERE (%s IS NOT NULL AND email = %s)
                          OR (%s IS NOT NULL AND phone_number = %s)
                       LIMIT 1""",
                    (email, email, phone, phone),
                )
                existing = cursor.fetchone()
                if existing:
                    cursor.execute(
                        """UPDATE passenger
                           SET passenger_name = %s,
                               age = COALESCE(%s, age),
                               date_of_birth = COALESCE(%s, date_of_birth)
                           WHERE passenger_id = %s""",
                        (name, age, birth_date, existing["passenger_id"]),
                    )
                    connection.commit()
                    return jsonify({"passenger_id": existing["passenger_id"], "passenger_name": name}), 200

            cursor.execute(
                "INSERT INTO passenger (passenger_name, email, phone_number, age, date_of_birth) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    name,
                    email,
                    phone,
                    age,
                    birth_date,
                ),
            )
            connection.commit()
            return jsonify({"passenger_id": cursor.lastrowid, "passenger_name": name}), 201
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @app.post("/api/bookings")
    def create_booking():
        body = _body_object()
        passenger_data = body.get("passenger")
        passenger_id = body.get("passenger_id")
        if passenger_id is not None:
            passenger_id = _positive_int(passenger_id, "passenger_id")
        elif not isinstance(passenger_data, dict):
            raise ApiError("Provide passenger_id or a passenger object.")
        run_id = _positive_int(body.get("run_id"), "run_id")
        seat_ids = body.get("seat_ids")
        if not isinstance(seat_ids, list) or not seat_ids:
            raise ApiError("seat_ids must be a non-empty list.")
        seat_ids = sorted({_positive_int(item, "seat_id") for item in seat_ids})
        if len(seat_ids) != len(body["seat_ids"]):
            raise ApiError("seat_ids must not contain duplicates.")
        try:
            fare_rate = Decimal(os.getenv("RAIL_FARE_PER_KM", "0.75"))
        except InvalidOperation:
            raise ApiError("RAIL_FARE_PER_KM must be a positive decimal setting.", 503) from None
        if fare_rate <= 0:
            raise ApiError("Set RAIL_FARE_PER_KM locally before accepting bookings.", 503)

        placeholders = ",".join(["%s"] * len(seat_ids))
        connection = get_connection()
        try:
            connection.start_transaction()
            cursor = connection.cursor(dictionary=True)
            if passenger_id is not None:
                cursor.execute(
                    "SELECT passenger_id FROM passenger WHERE passenger_id = %s",
                    (passenger_id,),
                )
                if cursor.fetchone() is None:
                    raise ApiError("Passenger was not found.", 404)

            cursor.execute(
                """SELECT ts1.distance_from_source AS origin_distance,
                          ts2.distance_from_source AS destination_distance
                    FROM train_run r
                    JOIN train_stop ts1 ON ts1.train_id = r.train_id
                    JOIN station s1 ON s1.station_id = ts1.station_id
                    JOIN train_stop ts2 ON ts2.train_id = r.train_id
                    JOIN station s2 ON s2.station_id = ts2.station_id
                    WHERE r.run_id = %s AND s1.station_code = %s
                      AND s2.station_code = %s
                      AND ts1.stop_number < ts2.stop_number""",
                (run_id, str(body.get("origin", "")).strip().upper(),
                 str(body.get("destination", "")).strip().upper()),
            )
            route = cursor.fetchone()
            if route is None or route["origin_distance"] is None or route["destination_distance"] is None:
                raise ApiError("A valid forward route is required for this run.")
            distance = Decimal(route["destination_distance"]) - Decimal(route["origin_distance"])
            if distance <= 0:
                raise ApiError("The route distance is invalid.")
            fare = (distance * fare_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            cursor.execute(
                f"""SELECT run_seat_id, seat_id, seat_status FROM run_seat
                    WHERE run_id = %s AND seat_id IN ({placeholders})
                    ORDER BY seat_id FOR UPDATE""",
                (run_id, *seat_ids),
            )
            locked_seats = _rows(cursor)
            if len(locked_seats) != len(seat_ids):
                raise ApiError("One or more seats are not assigned to this run.", 409)
            unavailable = [row["seat_id"] for row in locked_seats if row["seat_status"] != "Available"]
            if unavailable:
                raise ApiError("One or more selected seats are no longer available.", 409)

            if passenger_id is None:
                passenger_name = str(passenger_data.get("passenger_name", "")).strip()
                if not passenger_name:
                    raise ApiError("passenger.passenger_name is required.")
                raw_age = passenger_data.get("age")
                if raw_age not in (None, ""):
                    try:
                        passenger_age = int(raw_age)
                    except (TypeError, ValueError):
                        raise ApiError("passenger.age must be between 5 and 120.") from None
                    if not 5 <= passenger_age <= 120:
                        raise ApiError("passenger.age must be between 5 and 120.")
                else:
                    passenger_age = None
                birth_date = passenger_data.get("date_of_birth") or None
                if birth_date:
                    try:
                        date.fromisoformat(birth_date)
                    except (TypeError, ValueError):
                        raise ApiError("passenger.date_of_birth must use YYYY-MM-DD format.") from None

                email = str(passenger_data.get("email", "")).strip() or None
                phone = str(passenger_data.get("phone_number", "")).strip() or None

                existing_passenger = None
                if email or phone:
                    cursor.execute(
                        """SELECT passenger_id FROM passenger
                           WHERE (%s IS NOT NULL AND email = %s)
                              OR (%s IS NOT NULL AND phone_number = %s)
                           LIMIT 1""",
                        (email, email, phone, phone),
                    )
                    existing_passenger = cursor.fetchone()

                if existing_passenger:
                    passenger_id = existing_passenger["passenger_id"]
                    cursor.execute(
                        """UPDATE passenger
                           SET passenger_name = %s,
                               age = COALESCE(%s, age),
                               date_of_birth = COALESCE(%s, date_of_birth)
                           WHERE passenger_id = %s""",
                        (passenger_name, passenger_age, birth_date, passenger_id),
                    )
                else:
                    cursor.execute(
                        """INSERT INTO passenger
                           (passenger_name, email, phone_number, age, date_of_birth)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (
                            passenger_name,
                            email,
                            phone,
                            passenger_age,
                            birth_date,
                        ),
                    )
                    passenger_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO booking (passenger_id, run_id, booking_status, total_fare) "
                "VALUES (%s, %s, 'Confirmed', %s)",
                (passenger_id, run_id, fare * len(seat_ids)),
            )
            booking_id = cursor.lastrowid
            cursor.executemany(
                "INSERT INTO booking_seat (booking_id, seat_id, seat_fare) VALUES (%s, %s, %s)",
                [(booking_id, seat_id, fare) for seat_id in seat_ids],
            )
            cursor.executemany(
                "UPDATE run_seat SET seat_status = 'Booked' "
                "WHERE run_id = %s AND seat_id = %s",
                [(run_id, seat_id) for seat_id in seat_ids],
            )
            connection.commit()
            return jsonify({
                "booking_id": booking_id,
                "passenger_id": passenger_id,
                "booking_status": "Confirmed",
                "seat_ids": seat_ids,
                "fare_per_seat": float(fare),
                "total_fare": float(fare * len(seat_ids)),
            }), 201
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @app.get("/api/bookings")
    def list_bookings():
        connection = get_connection()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """SELECT b.booking_id, b.booking_date, b.booking_status, b.total_fare,
                          p.passenger_name, p.email, p.phone_number,
                          r.journey_date, t.train_number, t.train_name, t.train_type,
                          GROUP_CONCAT(CONCAT(c.coach_number, '-', s.seat_number) ORDER BY c.coach_number, s.seat_number SEPARATOR ', ') AS seats
                   FROM booking b
                   JOIN passenger p ON p.passenger_id = b.passenger_id
                   JOIN train_run r ON r.run_id = b.run_id
                   JOIN train t ON t.train_id = r.train_id
                   LEFT JOIN booking_seat bs ON bs.booking_id = b.booking_id
                   LEFT JOIN seat s ON s.seat_id = bs.seat_id
                   LEFT JOIN coach c ON c.coach_id = s.coach_id
                   GROUP BY b.booking_id, b.booking_date, b.booking_status, b.total_fare,
                            p.passenger_name, p.email, p.phone_number, r.journey_date,
                            t.train_number, t.train_name, t.train_type
                   ORDER BY b.booking_id DESC
                   LIMIT 15"""
            )
            return jsonify(_json_value(_rows(cursor)))
        finally:
            connection.close()

    @app.get("/api/bookings/<int:booking_id>")
    def get_booking(booking_id):
        connection = get_connection()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """SELECT b.booking_id, b.booking_date, b.booking_status, b.total_fare,
                          p.passenger_id, p.passenger_name, p.email, p.phone_number,
                          r.run_id, r.journey_date,
                          t.train_number, t.train_name, t.train_type
                   FROM booking b
                   JOIN passenger p ON p.passenger_id = b.passenger_id
                   JOIN train_run r ON r.run_id = b.run_id
                   JOIN train t ON t.train_id = r.train_id
                   WHERE b.booking_id = %s""",
                (booking_id,)
            )
            booking = cursor.fetchone()
            if booking is None:
                raise ApiError("Booking was not found.", 404)

            cursor.execute(
                """SELECT bs.seat_id, bs.seat_fare, s.seat_number, s.berth_type,
                          c.coach_number, c.coach_type
                   FROM booking_seat bs
                   JOIN seat s ON s.seat_id = bs.seat_id
                   JOIN coach c ON c.coach_id = s.coach_id
                   WHERE bs.booking_id = %s
                   ORDER BY c.coach_number, s.seat_number""",
                (booking_id,)
            )
            booking["seats"] = _rows(cursor)
            return jsonify(_json_value(booking))
        finally:
            connection.close()

    @app.post("/api/bookings/<int:booking_id>/cancel")
    def cancel_booking(booking_id):
        connection = get_connection()
        try:
            connection.start_transaction()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT run_id, booking_status FROM booking WHERE booking_id = %s FOR UPDATE",
                (booking_id,),
            )
            booking = cursor.fetchone()
            if booking is None:
                raise ApiError("Booking was not found.", 404)
            if booking["booking_status"] == "Cancelled":
                raise ApiError("Booking is already cancelled.", 409)
            cursor.execute(
                "SELECT seat_id FROM booking_seat WHERE booking_id = %s ORDER BY seat_id",
                (booking_id,),
            )
            seat_ids = [row["seat_id"] for row in _rows(cursor)]
            if seat_ids:
                placeholders = ",".join(["%s"] * len(seat_ids))
                cursor.execute(
                    f"""SELECT run_seat_id FROM run_seat
                        WHERE run_id = %s AND seat_id IN ({placeholders})
                        ORDER BY seat_id FOR UPDATE""",
                    (booking["run_id"], *seat_ids),
                )
                locked_rows = _rows(cursor)
                if len(locked_rows) != len(seat_ids):
                    raise ApiError("The booking seat inventory is inconsistent.", 409)
                cursor.executemany(
                    "UPDATE run_seat SET seat_status = 'Available' "
                    "WHERE run_id = %s AND seat_id = %s",
                    [(booking["run_id"], seat_id) for seat_id in seat_ids],
                )
            cursor.execute(
                "UPDATE booking SET booking_status = 'Cancelled' WHERE booking_id = %s",
                (booking_id,),
            )
            connection.commit()
            return jsonify({"booking_id": booking_id, "booking_status": "Cancelled"})
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    return app


def inspect_database() -> int:
    connection = None
    try:
        connection = get_connection()
        print(json.dumps(inspect_schema(connection), indent=2, default=str))
        return 0
    except Exception as exc:
        print(f"Schema inspection failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


app = create_app()


if __name__ == "__main__":
    if "--inspect-schema" in sys.argv:
        raise SystemExit(inspect_database())
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=True)
