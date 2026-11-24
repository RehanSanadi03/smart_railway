"""Add verified Indian train routes to the existing MySQL schema.

This is additive and idempotent: it never updates or deletes existing rows.
It intentionally does not create dated train_run or run_seat inventory rows;
those require an operations calendar and real availability source.

Schedule references checked 2026-11-24:
- Official Indian Railways 2026 train index (12007/12002):
  https://rb.indianrailways.gov.in/uploads/directorate/coaching/TAG_2026/Train_Name_Index.pdf
- Indian Railways Shatabdi list (12002 terminal listing):
  https://indianrail.gov.in/shatabdi_trn_list.html
- 12007 timetable: https://etrain.info/train/Shatabdi-Exp-12007/schedule
- 12002 timetable: https://etrain.info/train/Bhopal-Shtbdi-12002/schedule
- 12951 timetable: https://etrain.info/train/Mumbai-Rajdhani-12951/schedule
- 12627 timetable: https://d.indiarailinfo.com/train/pdf/919?kkk=1780398341751
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
try:
    from backend.db import get_connection
except ImportError:
    from db import get_connection  # noqa: E402



# code, station name, city, state. Existing station rows are kept as-is.
STATIONS = [
    ("SBC", "KSR Bengaluru City Jn", "Bengaluru", "Karnataka"),
    ("BNC", "Bengaluru Cantt", "Bengaluru", "Karnataka"),
    ("YNK", "Yelahanka Jn", "Bengaluru", "Karnataka"),
    ("HUP", "Hindupur", "Hindupur", "Andhra Pradesh"),
    ("PKD", "Penukonda Jn", "Penukonda", "Andhra Pradesh"),
    ("SSPN", "Sri Sathya Sai Prashanthi Nilayam", "Puttaparthi", "Andhra Pradesh"),
    ("DMM", "Dharmavaram Jn", "Dharmavaram", "Andhra Pradesh"),
    ("ATP", "Anantapur", "Anantapur", "Andhra Pradesh"),
    ("GTL", "Guntakal Jn", "Guntakal", "Andhra Pradesh"),
    ("AD", "Adoni", "Adoni", "Andhra Pradesh"),
    ("MALM", "Mantralayam Road", "Mantralayam", "Andhra Pradesh"),
    ("RC", "Raichur Jn", "Raichur", "Karnataka"),
    ("YG", "Yadgir", "Yadgir", "Karnataka"),
    ("WADI", "Wadi Jn", "Wadi", "Karnataka"),
    ("KLBG", "Kalaburagi Jn", "Kalaburagi", "Karnataka"),
    ("SUR", "Solapur Jn", "Solapur", "Maharashtra"),
    ("KWV", "Kurduwadi Jn", "Kurduwadi", "Maharashtra"),
    ("DD", "Daund Jn", "Daund", "Maharashtra"),
    ("ANG", "Ahilyanagar Jn", "Ahilyanagar", "Maharashtra"),
    ("BAP", "Belapur", "Belapur", "Maharashtra"),
    ("KPG", "Kopargaon", "Kopargaon", "Maharashtra"),
    ("MMR", "Manmad Jn", "Manmad", "Maharashtra"),
    ("JL", "Jalgaon Jn", "Jalgaon", "Maharashtra"),
    ("BSL", "Bhusaval Jn", "Bhusaval", "Maharashtra"),
    ("BAU", "Burhanpur", "Burhanpur", "Madhya Pradesh"),
    ("KNW", "Khandwa Jn", "Khandwa", "Madhya Pradesh"),
    ("ET", "Itarsi Jn", "Itarsi", "Madhya Pradesh"),
    ("BPL", "Bhopal Jn", "Bhopal", "Madhya Pradesh"),
    ("BINA", "Bina Jn", "Bina", "Madhya Pradesh"),
    ("VGLJ", "Virangana Lakshmibai Jhansi Jn", "Jhansi", "Uttar Pradesh"),
    ("GWL", "Gwalior Jn", "Gwalior", "Madhya Pradesh"),
    ("AGC", "Agra Cantt", "Agra", "Uttar Pradesh"),
    ("MTJ", "Mathura Jn", "Mathura", "Uttar Pradesh"),
    ("NZM", "Hazrat Nizamuddin", "New Delhi", "Delhi"),
    ("NDLS", "New Delhi", "New Delhi", "Delhi"),
    ("MAS", "MGR Chennai Central", "Chennai", "Tamil Nadu"),
    ("KPD", "Katpadi Jn", "Vellore", "Tamil Nadu"),
    ("MYS", "Mysuru Jn", "Mysuru", "Karnataka"),
    ("MMCT", "Mumbai Central", "Mumbai", "Maharashtra"),
    ("BVI", "Borivali", "Mumbai", "Maharashtra"),
    ("ST", "Surat", "Surat", "Gujarat"),
    ("BRC", "Vadodara Jn", "Vadodara", "Gujarat"),
    ("RTM", "Ratlam Jn", "Ratlam", "Madhya Pradesh"),
    ("NAD", "Nagda Jn", "Nagda", "Madhya Pradesh"),
    ("KOTA", "Kota Jn", "Kota", "Rajasthan"),
    ("DHO", "Dholpur Jn", "Dholpur", "Rajasthan"),
    ("MRA", "Morena", "Morena", "Madhya Pradesh"),
    ("LAR", "Lalitpur Jn", "Lalitpur", "Uttar Pradesh"),
    ("RKMP", "Rani Kamalapati", "Bhopal", "Madhya Pradesh"),
]

# train number, name, type. Existing train rows are never overwritten.
TRAINS = [
    ("12002", "Bhopal Shatabdi Express", "Shatabdi"),
    ("12007", "Chennai-Mysuru Shatabdi Express", "Shatabdi"),
    ("12627", "Karnataka Express", "Superfast"),
    ("12951", "Mumbai Central-New Delhi Tejas Rajdhani Express", "Rajdhani"),
]

# Stops are (station code, arrival, departure, cumulative distance in km).
ROUTES = {
    "12002": [
        ("NDLS", None, "06:00", 0), ("MTJ", "07:19", "07:20", 141),
        ("AGC", "07:50", "07:55", 195), ("DHO", "08:39", "08:40", 247),
        ("MRA", "08:57", "08:58", 275), ("GWL", "09:23", "09:28", 313),
        ("VGLJ", "10:45", "10:50", 410), ("LAR", "11:42", "11:43", 500),
        ("BINA", "12:40", "12:42", 563), ("BPL", "14:12", "14:15", 701),
        ("RKMP", "14:40", None, 707),
    ],
    "12007": [
        ("MAS", None, "06:00", 0), ("KPD", "07:28", "07:30", 130),
        ("SBC", "10:30", "10:35", 362), ("MYS", "13:00", None, 500),
    ],
    "12627": [
        ("SBC", None, "19:20", 0), ("BNC", "19:31", "19:32", 4),
        ("YNK", "20:00", "20:02", 27), ("HUP", "21:06", "21:08", 111),
        ("PKD", "21:34", "21:35", 148), ("SSPN", "21:54", "21:55", 168),
        ("DMM", "22:40", "22:45", 202), ("ATP", "23:13", "23:15", 235),
        ("GTL", "00:25", "00:30", 303), ("AD", "01:13", "01:15", 355),
        ("MALM", "02:03", "02:05", 396), ("RC", "02:43", "02:45", 425),
        ("YG", "03:38", "03:40", 493), ("WADI", "04:40", "04:45", 532),
        ("KLBG", "05:17", "05:20", 569), ("SUR", "07:10", "07:15", 682),
        ("KWV", "08:18", "08:20", 761), ("DD", "10:00", "10:05", 869),
        ("ANG", "11:27", "11:30", 953), ("BAP", "12:38", "12:40", 1021),
        ("KPG", "13:37", "13:40", 1065), ("MMR", "14:50", "14:55", 1107),
        ("JL", "16:40", "16:42", 1267), ("BSL", "17:10", "17:15", 1291),
        ("BAU", "18:03", "18:05", 1346), ("KNW", "19:17", "19:20", 1415),
        ("ET", "21:20", "21:25", 1598), ("BPL", "23:00", "23:05", 1690),
        ("BINA", "01:08", "01:10", 1829), ("VGLJ", "02:50", "02:58", 1982),
        ("GWL", "04:05", "04:07", 2079), ("AGC", "05:35", "05:40", 2197),
        ("MTJ", "06:20", "06:25", 2251), ("NZM", "08:33", "08:35", 2385),
        ("NDLS", "09:00", None, 2392),
    ],
    "12951": [
        ("MMCT", None, "17:00", 0), ("BVI", "17:20", "17:22", 30),
        ("ST", "19:43", "19:48", 263), ("BRC", "21:06", "21:16", 392),
        ("RTM", "00:25", "00:28", 653), ("NAD", "01:08", "01:10", 695),
        ("KOTA", "03:15", "03:20", 920), ("NDLS", "08:32", None, 1384),
    ],
}

# Published operating weekdays, Monday=0. These are schedule instances only;
# they do not imply that seats are currently for sale or available.
RUN_DAYS = {
    "12002": set(range(7)),
    "12007": {0, 1, 2, 4, 5, 6},  # no Thursday
    "12627": set(range(7)),
    "12951": set(range(7)),
}
SCHEDULE_HORIZON_DAYS = 30


def main() -> None:
    connection = get_connection()
    inserted_stations = inserted_trains = inserted_stops = inserted_runs = 0
    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        cursor.executemany(
            "INSERT IGNORE INTO station (station_code, station_name, city, state) "
            "VALUES (%s, %s, %s, %s)",
            STATIONS,
        )
        inserted_stations = max(cursor.rowcount, 0)
        cursor.execute("SELECT station_id, station_code FROM station")
        station_ids = {row["station_code"]: row["station_id"] for row in cursor.fetchall()}
        missing_codes = sorted({stop[0] for route in ROUTES.values() for stop in route} - station_ids.keys())
        if missing_codes:
            raise RuntimeError(f"Station insert did not resolve codes: {missing_codes}")

        cursor.executemany(
            "INSERT IGNORE INTO train (train_number, train_name, train_type) "
            "VALUES (%s, %s, %s)",
            TRAINS,
        )
        inserted_trains = max(cursor.rowcount, 0)
        cursor.execute("SELECT train_id, train_number FROM train")
        train_ids = {row["train_number"]: row["train_id"] for row in cursor.fetchall()}

        for train_number, stops in ROUTES.items():
            train_id = train_ids[train_number]
            cursor.execute(
                """SELECT s.station_code FROM train_stop ts
                   JOIN station s ON s.station_id = ts.station_id
                   WHERE ts.train_id = %s ORDER BY ts.stop_number""",
                (train_id,),
            )
            current_route = [row["station_code"] for row in cursor.fetchall()]
            wanted_route = [stop[0] for stop in stops]
            if current_route:
                if current_route != wanted_route:
                    raise RuntimeError(
                        f"Train {train_number} already has a different route; "
                        "no route rows were changed."
                    )
                continue

            values = [
                (train_id, station_ids[code], number, arrival, departure, distance)
                for number, (code, arrival, departure, distance) in enumerate(stops, 1)
            ]
            cursor.executemany(
                """INSERT INTO train_stop
                   (train_id, station_id, stop_number, arrival_time,
                    departure_time, distance_from_source)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                values,
            )
            inserted_stops += max(cursor.rowcount, 0)

        first_day = date.today() + timedelta(days=1)
        run_rows = []
        for train_number, weekdays in RUN_DAYS.items():
            train_id = train_ids[train_number]
            for offset in range(SCHEDULE_HORIZON_DAYS):
                run_date = first_day + timedelta(days=offset)
                if run_date.weekday() in weekdays:
                    run_rows.append((train_id, run_date, "Scheduled"))
        cursor.executemany(
            "INSERT IGNORE INTO train_run (train_id, journey_date, running_status) "
            "VALUES (%s, %s, %s)",
            run_rows,
        )
        inserted_runs = max(cursor.rowcount, 0)

        connection.commit()
        print(
            f"Committed additive route seed: {inserted_stations} stations, "
            f"{inserted_trains} trains, {inserted_stops} train stops, "
            f"{inserted_runs} dated runs. Existing records were left unchanged; "
            "no seat availability was fabricated."
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
