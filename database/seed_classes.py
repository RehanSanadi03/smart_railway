"""Add AC First Class (1st Tier) and AC 2 Tier coaches, seats, and run_seats."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
try:
    from backend.db import get_connection
except ImportError:
    from db import get_connection


COACHES_TO_ADD = [
    # (train_number, coach_number, coach_type)
    ("12627", "H1", "AC First Class"),
    ("12627", "A1", "AC 2 Tier"),
    ("12628", "H1", "AC First Class"),
    ("12628", "A1", "AC 2 Tier"),
    ("12951", "H1", "AC First Class"),
    ("12952", "H1", "AC First Class"),
    ("20654", "A1", "AC 2 Tier"),
    ("20654", "H1", "AC First Class"),
    ("20653", "A1", "AC 2 Tier"),
    ("20653", "H1", "AC First Class"),
]

BERTH_PATTERN = [
    "Lower", "Upper",
    "Lower", "Upper",
    "Lower", "Upper",
    "Side Lower", "Side Upper"
]

def main():
    conn = get_connection()
    try:
        conn.start_transaction()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT train_id, train_number FROM train")
        train_map = {r["train_number"]: r["train_id"] for r in cur.fetchall()}

        # 1. Insert coaches
        for train_num, c_num, c_type in COACHES_TO_ADD:
            if train_num not in train_map:
                continue
            tid = train_map[train_num]
            cur.execute(
                "INSERT IGNORE INTO coach (train_id, coach_number, coach_type) VALUES (%s, %s, %s)",
                (tid, c_num, c_type)
            )

        # 2. Insert seats for any coach lacking seats
        cur.execute("SELECT coach_id, coach_type FROM coach")
        all_coaches = cur.fetchall()
        for coach in all_coaches:
            cid = coach["coach_id"]
            cur.execute("SELECT COUNT(*) AS cnt FROM seat WHERE coach_id = %s", (cid,))
            if cur.fetchone()["cnt"] == 0:
                # AC First Class typically has fewer cabins/seats, e.g. 24 or 72
                # In our schema CHECK ((seat_number between 1 and 72))
                num_seats = 24 if coach["coach_type"] == "AC First Class" else (48 if coach["coach_type"] == "AC 2 Tier" else 72)
                seat_rows = [
                    (cid, s_num, "Lower" if s_num % 2 == 1 else "Upper")
                    for s_num in range(1, num_seats + 1)
                ]
                cur.executemany(
                    "INSERT IGNORE INTO seat (coach_id, seat_number, berth_type) VALUES (%s, %s, %s)",
                    seat_rows
                )

        # 3. Add run_seat for all future runs for these new coaches
        today = date.today()
        cur.execute("""
            SELECT c.coach_id, c.train_id, s.seat_id
            FROM coach c
            JOIN seat s ON s.coach_id = c.coach_id
            WHERE c.coach_number IN ('H1', 'A1')
        """)
        new_coach_seats = cur.fetchall()
        train_new_seats: dict[int, list[int]] = {}
        for r in new_coach_seats:
            train_new_seats.setdefault(r["train_id"], []).append(r["seat_id"])

        cur.execute("SELECT run_id, train_id FROM train_run WHERE journey_date >= %s", (today,))
        runs = cur.fetchall()

        inserted_run_seats = 0
        for run in runs:
            rid = run["run_id"]
            tid = run["train_id"]
            seats = train_new_seats.get(tid, [])
            if not seats:
                continue

            rows = [
                (rid, sid, "Booked" if idx % 7 == 0 else "Available")
                for idx, sid in enumerate(seats)
            ]
            cur.executemany(
                "INSERT IGNORE INTO run_seat (run_id, seat_id, seat_status) VALUES (%s, %s, %s)",
                rows
            )
            inserted_run_seats += max(cur.rowcount, 0)

        conn.commit()
        print(f"Successfully added AC First Class and 2 Tier classes. Run seats added: {inserted_run_seats}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
