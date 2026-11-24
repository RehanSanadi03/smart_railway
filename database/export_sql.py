"""Export live MySQL schema and sample data to SQL files."""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import date, datetime, time, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
try:
    from backend.db import get_connection
except ImportError:
    from db import get_connection  # type: ignore[import-untyped]


TABLES = [
    "station",
    "train",
    "train_stop",
    "coach",
    "seat",
    "train_run",
    "run_seat",
    "passenger",
    "booking",
    "booking_seat"
]

def format_val(val):
    if val is None:
        return "NULL"
    if isinstance(val, (int, float, Decimal)):
        return str(val)
    if isinstance(val, (date, datetime, time, timedelta)):
        return f"'{str(val)}'"
    escaped = str(val).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"

def export_schema(conn, out_path):
    cur = conn.cursor(dictionary=True)
    lines = [
        "-- Smart Railway Management System - Database Schema",
        "-- Compatible with MySQL 8.0+",
        "",
        "CREATE DATABASE IF NOT EXISTS smart_railway;",
        "USE smart_railway;",
        "",
        "SET FOREIGN_KEY_CHECKS = 0;",
    ]

    for table in reversed(TABLES):
        lines.append(f"DROP TABLE IF EXISTS `{table}`;")
    lines.append("")
    lines.append("SET FOREIGN_KEY_CHECKS = 1;")
    lines.append("")

    for table in TABLES:
        cur.execute(f"SHOW CREATE TABLE `{table}`")
        row = cur.fetchone()
        create_stmt = row["Create Table"]
        lines.append(f"-- Table structure for table `{table}`")
        lines.append(f"{create_stmt};\n")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Exported schema to {out_path}")

def export_sample_data(conn, out_path):
    cur = conn.cursor(dictionary=True)
    lines = [
        "-- Smart Railway Management System - Sample Data Seed",
        "-- Contains realistic data for stations, trains, stops, coaches, seats, runs, and bookings",
        "",
        "USE smart_railway;",
        "",
        "SET FOREIGN_KEY_CHECKS = 0;",
    ]

    for table in TABLES:
        cur.execute(f"SELECT * FROM `{table}`")
        rows = cur.fetchall()
        if not rows:
            continue
        lines.append(f"\n-- Data for table `{table}` ({len(rows)} rows)")
        cols = list(rows[0].keys())
        col_names = ", ".join(f"`{c}`" for c in cols)
        
        # Batch into chunks of 100 rows
        for i in range(0, len(rows), 100):
            chunk = rows[i:i+100]
            val_lines = []
            for r in chunk:
                vals = [format_val(r[c]) for c in cols]
                val_lines.append(f"  ({', '.join(vals)})")
            lines.append(f"INSERT INTO `{table}` ({col_names}) VALUES\n" + ",\n".join(val_lines) + ";")

    lines.append("\nSET FOREIGN_KEY_CHECKS = 1;")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Exported sample data to {out_path}")

def main():
    conn = get_connection()
    try:
        db_dir = Path(__file__).resolve().parents[1] / "database"
        export_schema(conn, db_dir / "schema.sql")
        export_sample_data(conn, db_dir / "sample_data.sql")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
