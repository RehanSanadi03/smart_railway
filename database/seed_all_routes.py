"""Seed complete two-way Indian train routes, stops, runs, and seats.

Idempotent: Uses INSERT IGNORE so all existing records are preserved.
Ensures both forward and return routes exist for all major station pairs,
so searches work in both directions (e.g. SBC -> NDLS AND NDLS -> SBC,
MAS -> MYS AND MYS -> MAS, MMCT -> NDLS AND NDLS -> MMCT, etc.).
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


# Format: (train_number, train_name, train_type)
NEW_TRAINS = [
    ("12628", "Karnataka Express (Return)", "Express"),
    ("12008", "Mysuru-Chennai Shatabdi Express", "Shatabdi"),
    ("12001", "New Delhi Shatabdi Express", "Shatabdi"),
    ("12952", "New Delhi-Mumbai Tejas Rajdhani Express", "Rajdhani"),
    ("20653", "KSR Bengaluru-Belagavi Superfast", "Superfast"),
    ("16536", "Gol Gumbaz Express (Return)", "Express"),
    ("17326", "Vishwamanava Express (Return)", "Express"),
    ("12124", "Deccan Express (Pune-Mumbai)", "Superfast"),
    ("12123", "Deccan Express (Mumbai-Pune)", "Superfast"),
]

# Stops are: (station_code, arrival_time, departure_time, distance_from_source)
NEW_ROUTES = {
    # 1. Karnataka Express Return: NDLS -> SBC (35 stops)
    "12628": [
        ("NDLS", None, "20:20", 0), ("NZM", "20:36", "20:38", 7),
        ("MTJ", "21:58", "22:00", 141), ("AGC", "22:45", "22:50", 195),
        ("GWL", "00:46", "00:48", 313), ("VGLJ", "02:20", "02:28", 410),
        ("BINA", "04:40", "04:45", 563), ("BPL", "06:25", "06:30", 702),
        ("ET", "08:10", "08:20", 794), ("KNW", "10:58", "11:00", 977),
        ("BAU", "11:53", "11:55", 1046), ("BSL", "13:00", "13:05", 1101),
        ("JL", "13:33", "13:35", 1125), ("MMR", "15:38", "15:40", 1285),
        ("KPG", "16:48", "16:50", 1327), ("BAP", "17:33", "17:35", 1371),
        ("ANG", "18:47", "18:50", 1439), ("DD", "20:45", "20:50", 1523),
        ("KWV", "22:18", "22:20", 1631), ("SUR", "23:45", "23:50", 1710),
        ("KLBG", "01:22", "01:25", 1823), ("WADI", "02:20", "02:25", 1860),
        ("YG", "02:59", "03:00", 1899), ("RC", "03:58", "04:00", 1967),
        ("MALM", "04:29", "04:30", 1996), ("AD", "05:09", "05:10", 2037),
        ("GTL", "06:25", "06:30", 2089), ("ATP", "07:39", "07:40", 2157),
        ("DMM", "08:43", "08:45", 2190), ("SSPN", "09:24", "09:25", 2224),
        ("PKD", "09:44", "09:45", 2244), ("HUP", "10:24", "10:25", 2281),
        ("YNK", "11:38", "11:40", 2365), ("BNC", "11:58", "12:00", 2388),
        ("SBC", "12:30", None, 2392),
    ],

    # 2. Shatabdi Return: MYS -> MAS (4 stops)
    "12008": [
        ("MYS", None, "14:15", 0), ("SBC", "16:15", "16:20", 138),
        ("KPD", "19:23", "19:25", 370), ("MAS", "21:30", None, 500),
    ],

    # 3. Bhopal Shatabdi Return: RKMP -> NDLS (11 stops)
    "12001": [
        ("RKMP", None, "15:15", 0), ("BPL", "15:27", "15:30", 6),
        ("BINA", "17:00", "17:02", 144), ("LAR", "17:48", "17:50", 207),
        ("VGLJ", "18:40", "18:45", 297), ("GWL", "19:40", "19:45", 394),
        ("MRA", "20:10", "20:11", 432), ("DHO", "20:34", "20:35", 460),
        ("AGC", "21:10", "21:15", 512), ("MTJ", "21:49", "21:50", 566),
        ("NDLS", "23:55", None, 707),
    ],

    # 4. Tejas Rajdhani Return: NDLS -> MMCT (8 stops)
    "12952": [
        ("NDLS", None, "16:55", 0), ("KOTA", "21:30", "21:40", 464),
        ("NAD", "00:05", "00:07", 689), ("RTM", "00:42", "00:45", 731),
        ("BRC", "03:40", "03:50", 992), ("ST", "05:13", "05:18", 1121),
        ("BVI", "07:38", "07:40", 1354), ("MMCT", "08:35", None, 1384),
    ],

    # 5. Existing train 20654: Belagavi to Bengaluru (BGM -> SBC)
    "20654": [
        ("BGM", None, "06:00", 0), ("DWR", "07:40", "07:42", 122),
        ("UBL", "08:05", "08:15", 142), ("YNK", "13:45", "13:47", 595),
        ("SBC", "14:15", None, 611),
    ],

    # 6. Return Bengaluru to Belagavi (SBC -> BGM)
    "20653": [
        ("SBC", None, "14:50", 0), ("YNK", "15:10", "15:12", 16),
        ("UBL", "20:45", "20:55", 469), ("DWR", "21:20", "21:22", 489),
        ("BGM", "23:15", None, 611),
    ],

    # 7. Existing train 16535: Gol Gumbaz Express (MYS -> SUR via SBC, UBL)
    "16535": [
        ("MYS", None, "15:45", 0), ("SBC", "18:05", "18:20", 138),
        ("YNK", "18:48", "18:50", 154), ("DWR", "02:00", "02:02", 590),
        ("UBL", "02:25", "02:35", 610), ("KLBG", "08:50", "08:55", 940),
        ("SUR", "10:30", None, 1053),
    ],

    # 8. Return Gol Gumbaz Express (SUR -> MYS via UBL, SBC)
    "16536": [
        ("SUR", None, "14:10", 0), ("KLBG", "15:40", "15:45", 113),
        ("UBL", "22:00", "22:10", 443), ("DWR", "22:33", "22:35", 463),
        ("YNK", "06:18", "06:20", 899), ("SBC", "07:15", "07:30", 915),
        ("MYS", "10:15", None, 1053),
    ],

    # 9. Existing train 17325: Vishwamanava Express (BGM -> MYS via SBC)
    "17325": [
        ("BGM", None, "05:45", 0), ("DWR", "07:15", "07:17", 122),
        ("UBL", "07:45", "07:55", 142), ("YNK", "16:50", "16:52", 595),
        ("SBC", "17:40", "17:55", 611), ("MYS", "20:40", None, 749),
    ],

    # 10. Return Vishwamanava Express (MYS -> BGM via SBC)
    "17326": [
        ("MYS", None, "05:45", 0), ("SBC", "08:45", "09:00", 138),
        ("YNK", "09:22", "09:24", 154), ("UBL", "18:15", "18:25", 607),
        ("DWR", "18:48", "18:50", 627), ("BGM", "20:45", None, 749),
    ],

    # 11. Deccan Express: Pune to Mumbai (PUNE -> MMCT)
    "12124": [
        ("PUNE", None, "07:15", 0), ("KWV", "08:55", "08:57", 100),
        ("SUR", "10:30", "10:35", 180), ("BVI", "13:20", "13:22", 340),
        ("MMCT", "14:05", None, 370),
    ],

    # 12. Deccan Express: Mumbai to Pune (MMCT -> PUNE)
    "12123": [
        ("MMCT", None, "17:10", 0), ("BVI", "17:45", "17:47", 30),
        ("SUR", "20:30", "20:35", 190), ("KWV", "22:05", "22:07", 270),
        ("PUNE", "23:45", None, 370),
    ],
}

COACH_MAP = {
    "12628": [("S1", "Sleeper"), ("S2", "Sleeper"), ("B1", "AC 3 Tier")],
    "12008": [("C1", "AC Chair Car"), ("C2", "AC Chair Car"), ("E1", "Executive Chair Car")],
    "12001": [("C1", "AC Chair Car"), ("C2", "AC Chair Car"), ("E1", "Executive Chair Car")],
    "12952": [("B1", "AC 3 Tier"), ("B2", "AC 3 Tier"), ("A1", "AC 2 Tier")],
    "20653": [("S1", "Sleeper"), ("S2", "Sleeper"), ("B1", "AC 3 Tier")],
    "16536": [("S1", "Sleeper"), ("S2", "Sleeper"), ("B1", "AC 3 Tier")],
    "17326": [("S1", "Sleeper"), ("S2", "Sleeper"), ("B1", "AC 3 Tier")],
    "12124": [("C1", "AC Chair Car"), ("C2", "AC Chair Car"), ("S1", "Sleeper")],
    "12123": [("C1", "AC Chair Car"), ("C2", "AC Chair Car"), ("S1", "Sleeper")],
    # Existing trains needing coaches if missing:
    "16535": [("S1", "Sleeper"), ("S2", "Sleeper"), ("B1", "AC 3 Tier")],
    "17325": [("S1", "Sleeper"), ("S2", "Sleeper"), ("B1", "AC 3 Tier")],
}

BERTH_PATTERN = [
    "Lower", "Middle", "Upper",
    "Lower", "Middle", "Upper",
    "Side Lower", "Side Upper"
]


def main():
    conn = get_connection()
    try:
        conn.start_transaction()
        cur = conn.cursor(dictionary=True)

        # 1. Insert new trains
        cur.executemany(
            "INSERT IGNORE INTO train (train_number, train_name, train_type) VALUES (%s, %s, %s)",
            NEW_TRAINS,
        )

        # Get all train IDs
        cur.execute("SELECT train_id, train_number FROM train")
        train_map = {r["train_number"]: r["train_id"] for r in cur.fetchall()}

        # Get all station IDs
        cur.execute("SELECT station_id, station_code FROM station")
        station_map = {r["station_code"]: r["station_id"] for r in cur.fetchall()}

        # 2. Insert stops for each route
        inserted_stops = 0
        for train_num, stops in NEW_ROUTES.items():
            if train_num not in train_map:
                continue
            tid = train_map[train_num]

            # Check if stops already exist
            cur.execute("SELECT COUNT(*) AS cnt FROM train_stop WHERE train_id = %s", (tid,))
            if cur.fetchone()["cnt"] > 0:
                continue

            stop_values = []
            for num, (code, arr, dep, dist) in enumerate(stops, 1):
                if code not in station_map:
                    raise RuntimeError(f"Unknown station code {code}")
                stop_values.append((tid, station_map[code], num, arr, dep, dist))

            cur.executemany(
                """INSERT INTO train_stop
                   (train_id, station_id, stop_number, arrival_time, departure_time, distance_from_source)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                stop_values,
            )
            inserted_stops += len(stop_values)

        # 3. Insert coaches
        for train_num, coaches in COACH_MAP.items():
            if train_num not in train_map:
                continue
            tid = train_map[train_num]
            for c_num, c_type in coaches:
                cur.execute(
                    "INSERT IGNORE INTO coach (train_id, coach_number, coach_type) VALUES (%s, %s, %s)",
                    (tid, c_num, c_type),
                )

        # 4. Insert seats for each coach (1..72)
        cur.execute("SELECT coach_id FROM coach")
        for coach in cur.fetchall():
            cid = coach["coach_id"]
            cur.execute("SELECT COUNT(*) AS cnt FROM seat WHERE coach_id = %s", (cid,))
            if cur.fetchone()["cnt"] == 0:
                seat_rows = [
                    (cid, s_num, BERTH_PATTERN[(s_num - 1) % 8])
                    for s_num in range(1, 73)
                ]
                cur.executemany(
                    "INSERT IGNORE INTO seat (coach_id, seat_number, berth_type) VALUES (%s, %s, %s)",
                    seat_rows,
                )

        # 5. Schedule train_runs for all active trains (today + next 30 days)
        today = date.today()
        for train_num, tid in train_map.items():
            # Check if train has stops
            cur.execute("SELECT COUNT(*) AS cnt FROM train_stop WHERE train_id = %s", (tid,))
            if cur.fetchone()["cnt"] == 0:
                continue

            run_rows = [
                (tid, today + timedelta(days=offset), "Scheduled")
                for offset in range(31)
            ]
            cur.executemany(
                "INSERT IGNORE INTO train_run (train_id, journey_date, running_status) VALUES (%s, %s, %s)",
                run_rows,
            )

        # 6. Populate run_seat for all runs
        cur.execute("""
            SELECT c.train_id, s.seat_id
            FROM coach c
            JOIN seat s ON s.coach_id = c.coach_id
            ORDER BY c.train_id, s.seat_id
        """)
        train_seats: dict[int, list[int]] = {}
        for row in cur.fetchall():
            train_seats.setdefault(row["train_id"], []).append(row["seat_id"])

        cur.execute("SELECT DISTINCT run_id FROM run_seat")
        runs_with_seats = {r["run_id"] for r in cur.fetchall()}

        cur.execute("SELECT run_id, train_id FROM train_run WHERE journey_date >= %s", (today,))
        all_runs = cur.fetchall()

        inserted_run_seats = 0
        for run in all_runs:
            rid = run["run_id"]
            if rid in runs_with_seats:
                continue
            tid = run["train_id"]
            seats = train_seats.get(tid, [])
            if not seats:
                continue

            run_seat_rows = [
                (rid, sid, "Booked" if (idx % 20 == 0 or idx % 27 == 0) else "Available")
                for idx, sid in enumerate(seats)
            ]
            cur.executemany(
                "INSERT IGNORE INTO run_seat (run_id, seat_id, seat_status) VALUES (%s, %s, %s)",
                run_seat_rows,
            )
            inserted_run_seats += len(run_seat_rows)

        conn.commit()
        print(f"Successfully added return and regional routes:")
        print(f"  Stops added: {inserted_stops}")
        print(f"  Run seats added: {inserted_run_seats}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
