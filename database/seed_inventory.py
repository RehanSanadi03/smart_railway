"""Seed coaches, seats, and run_seat inventory for active train runs.

Idempotent: Uses INSERT IGNORE so existing records are preserved.
Ensures that all scheduled runs have real seat inventory in the database,
allowing train search, seat selection, booking, and cancellation to work end-to-end.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
try:
    from backend.db import get_connection
except ImportError:
    from db import get_connection


BERTH_PATTERN = [
    "Lower", "Middle", "Upper",
    "Lower", "Middle", "Upper",
    "Side Lower", "Side Upper"
]

COACH_CONFIG = {
    # train_number: [(coach_number, coach_type, total_seats)]
    "12002": [("C1", "AC Chair Car", 72), ("C2", "AC Chair Car", 72), ("E1", "Executive Chair Car", 72)],
    "12007": [("C1", "AC Chair Car", 72), ("C2", "AC Chair Car", 72), ("E1", "Executive Chair Car", 72)],
    "12627": [("S1", "Sleeper", 72), ("S2", "Sleeper", 72), ("S3", "Sleeper", 72), ("B1", "AC 3 Tier", 72)],
    "12951": [("B1", "AC 3 Tier", 72), ("B2", "AC 3 Tier", 72), ("A1", "AC 2 Tier", 72)],
    "20654": [("S1", "Sleeper", 72), ("S2", "Sleeper", 72), ("S3", "Sleeper", 72)],
}

RUN_DAYS = {
    "12002": set(range(7)),
    "12007": {0, 1, 2, 4, 5, 6},
    "12627": set(range(7)),
    "12951": set(range(7)),
    "20654": set(range(7)),
}


def main():
    conn = get_connection()
    try:
        conn.start_transaction()
        cur = conn.cursor(dictionary=True)

        # 1. Fetch train IDs
        cur.execute("SELECT train_id, train_number FROM train")
        train_map = {row["train_number"]: row["train_id"] for row in cur.fetchall()}

        # 2. Insert coaches
        inserted_coaches = 0
        for train_num, coaches in COACH_CONFIG.items():
            if train_num not in train_map:
                continue
            tid = train_map[train_num]
            for c_num, c_type, _ in coaches:
                cur.execute(
                    "INSERT IGNORE INTO coach (train_id, coach_number, coach_type) VALUES (%s, %s, %s)",
                    (tid, c_num, c_type)
                )
                inserted_coaches += max(cur.rowcount, 0)

        # 3. Fetch all coaches
        cur.execute("SELECT coach_id, train_id, coach_number FROM coach")
        all_coaches = cur.fetchall()

        # 4. Insert seats for each coach (1..72)
        inserted_seats = 0
        for coach in all_coaches:
            cid = coach["coach_id"]
            cur.execute("SELECT COUNT(*) AS cnt FROM seat WHERE coach_id = %s", (cid,))
            if cur.fetchone()["cnt"] == 0:
                seat_rows = []
                for s_num in range(1, 73):
                    b_type = BERTH_PATTERN[(s_num - 1) % 8]
                    seat_rows.append((cid, s_num, b_type))
                cur.executemany(
                    "INSERT IGNORE INTO seat (coach_id, seat_number, berth_type) VALUES (%s, %s, %s)",
                    seat_rows
                )
                inserted_seats += max(cur.rowcount, 0)

        # 5. Ensure today's run exists
        today = date.today()
        inserted_runs = 0
        for train_num, weekdays in RUN_DAYS.items():
            if train_num not in train_map:
                continue
            tid = train_map[train_num]
            for offset in range(31):
                d = today + timedelta(days=offset)
                if d.weekday() in weekdays:
                    cur.execute(
                        "INSERT IGNORE INTO train_run (train_id, journey_date, running_status) VALUES (%s, %s, 'Scheduled')",
                        (tid, d)
                    )
                    inserted_runs += max(cur.rowcount, 0)

        # 6. Fetch all runs and train-to-seat mappings
        cur.execute("""
            SELECT r.run_id, r.train_id, r.journey_date
            FROM train_run r
            WHERE r.journey_date >= %s
            ORDER BY r.journey_date, r.train_id
        """, (today,))
        runs = cur.fetchall()

        # Map train_id -> list of seat_ids
        cur.execute("""
            SELECT c.train_id, s.seat_id
            FROM coach c
            JOIN seat s ON s.coach_id = c.coach_id
            ORDER BY c.train_id, s.seat_id
        """)
        train_seats: dict[int, list[int]] = {}
        for row in cur.fetchall():
            train_seats.setdefault(row["train_id"], []).append(row["seat_id"])

        # 7. Insert run_seat for any run lacking seats
        cur.execute("SELECT DISTINCT run_id FROM run_seat")
        runs_with_seats = {row["run_id"] for row in cur.fetchall()}

        inserted_run_seats = 0
        for run in runs:
            rid = run["run_id"]
            if rid in runs_with_seats:
                continue
            tid = run["train_id"]
            seats = train_seats.get(tid, [])
            if not seats:
                continue

            # Populate run_seat: mark first 2-3 seats Booked as realistic initial bookings, rest Available
            run_seat_rows = []
            for idx, sid in enumerate(seats):
                status = "Booked" if (idx % 18 == 0 or idx % 23 == 0) else "Available"
                run_seat_rows.append((rid, sid, status))

            cur.executemany(
                "INSERT IGNORE INTO run_seat (run_id, seat_id, seat_status) VALUES (%s, %s, %s)",
                run_seat_rows
            )
            inserted_run_seats += max(cur.rowcount, 0)

        conn.commit()
        print(f"Inventory seed completed:")
        print(f"  Coaches added: {inserted_coaches}")
        print(f"  Seats added: {inserted_seats}")
        print(f"  Runs added: {inserted_runs}")
        print(f"  Run seats added: {inserted_run_seats}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
