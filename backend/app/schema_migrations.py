"""Minimal additive SQLite migrations for course-demo databases.

Never drop tables or overwrite user data. Existing databases from earlier
milestones need columns added because SQLAlchemy create_all() cannot add them.
"""
from sqlalchemy import inspect


ADDITIONS = {
    "dose_occurrences": {
        "deadline_at": "DATETIME",
        "reminder_count": "INTEGER NOT NULL DEFAULT 0",
        "clock_mode": "VARCHAR(20) NOT NULL DEFAULT 'SIMULATION'",
    },
    "device_events": {
        "patient_id": "INTEGER REFERENCES patients(id)",
        "device_id": "VARCHAR(30)",
        "slot": "INTEGER",
        "occurred_at": "DATETIME",
    },
    "alerts": {
        "recipient_id": "INTEGER REFERENCES users(id)",
        "status": "VARCHAR(30) NOT NULL DEFAULT 'PENDING'",
        "note": "VARCHAR(255)",
    },
    "simulation_state": {
        "patient_id": "INTEGER REFERENCES patients(id)",
        "clock_mode": "VARCHAR(20) NOT NULL DEFAULT 'SIMULATION'",
        "simulation_clock": "VARCHAR(40)",
    },
}


def upgrade_sqlite_schema(engine) -> None:
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as connection:
        existing_tables = set(inspect(connection).get_table_names())
        for table, columns in ADDITIONS.items():
            if table not in existing_tables:
                continue
            known = {row[1] for row in connection.exec_driver_sql(f'PRAGMA table_info("{table}")')}
            for name, definition in columns.items():
                if name not in known:
                    connection.exec_driver_sql(
                        f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}'
                    )
        # Retain the saved demo cursor when upgrading databases from the first release.
        connection.exec_driver_sql("""
            UPDATE simulation_state SET simulation_clock = virtual_clock
            WHERE simulation_clock IS NULL
        """)
        # The demo device has one patient; older databases did not store this link.
        connection.exec_driver_sql("""
            UPDATE simulation_state SET patient_id = (
                SELECT p.id FROM patients p JOIN users u ON p.caregiver_id = u.id
                WHERE u.email = 'caregiver-a@example.test'
                ORDER BY p.id LIMIT 1
            ) WHERE patient_id IS NULL AND device_id = 'SIM-001'
        """)
        # Old events with an occurrence can be safely attributed to its patient.
        connection.exec_driver_sql("""
            UPDATE device_events SET patient_id = (
                SELECT s.patient_id FROM dose_occurrences o
                JOIN medication_schedules s ON s.id = o.schedule_id
                WHERE o.id = device_events.occurrence_id
            ) WHERE patient_id IS NULL AND occurrence_id IS NOT NULL
        """)
        # For demo events without an occurrence, only associate an explicitly
        # identified SIM-001 device. Never expose arbitrary unassigned events.
        connection.exec_driver_sql("""
            UPDATE device_events SET patient_id = (
                SELECT patient_id FROM simulation_state WHERE device_id = 'SIM-001'
            ), device_id = 'SIM-001'
            WHERE patient_id IS NULL AND json_valid(payload)
              AND json_extract(payload, '$.device_id') = 'SIM-001'
        """)
        connection.exec_driver_sql("""
            UPDATE alerts SET recipient_id = (
                SELECT caregiver_id FROM patients WHERE patients.id = alerts.patient_id
            ) WHERE recipient_id IS NULL
        """)
        # Fail closed on historical duplicates rather than silently deleting data.
        connection.exec_driver_sql("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_dose_schedule_at
            ON dose_occurrences(schedule_id, scheduled_at)
        """)
        connection.exec_driver_sql("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_alert_occurrence_kind
            ON alerts(occurrence_id, kind) WHERE occurrence_id IS NOT NULL
        """)
