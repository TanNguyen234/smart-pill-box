import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent / "data" / "smartpill.sqlite3"
con = sqlite3.connect(db_path)
cur = con.cursor()

def add_col(table, col, col_type):
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        print(f"Added {col} to {table}")

add_col("simulation_state", "patient_id", "INTEGER")
add_col("dose_occurrences", "deadline_at", "DATETIME")
add_col("dose_occurrences", "reminder_count", "INTEGER DEFAULT 0")
add_col("device_events", "patient_id", "INTEGER")
add_col("device_events", "slot", "INTEGER")
add_col("device_events", "occurred_at", "DATETIME")
add_col("alerts", "recipient_id", "INTEGER")
add_col("alerts", "status", "TEXT DEFAULT 'PENDING'")
add_col("alerts", "note", "TEXT")

patient_1 = cur.execute("SELECT id FROM patients LIMIT 1").fetchone()
if patient_1:
    cur.execute("UPDATE simulation_state SET patient_id = ? WHERE patient_id IS NULL", (patient_1[0],))
    print(f"Updated simulation_state patient_id to {patient_1[0]}")

con.commit()
con.close()
print("Migration completed successfully!")
