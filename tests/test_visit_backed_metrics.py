from datetime import datetime, timedelta

from database.db import Database
from database.metrics_queries import MetricsQueries


def _insert_visit_with_history(db, room_id, start_dt, wait_s, provider_s, cleaning_s):
    seeing_dt = start_dt + timedelta(seconds=wait_s)
    needs_cleaning_dt = seeing_dt + timedelta(seconds=provider_s)
    cleaning_dt = needs_cleaning_dt + timedelta(seconds=60)
    available_dt = cleaning_dt + timedelta(seconds=cleaning_s)

    db.execute(
        "INSERT INTO visits (room_id, start_time, end_time) VALUES (?, ?, ?)",
        (room_id, start_dt.isoformat(sep=" "), available_dt.isoformat(sep=" ")),
    )

    transitions = [
        ("available", "waiting", start_dt),
        ("waiting", "seeing_provider", seeing_dt),
        ("seeing_provider", "needs_cleaning", needs_cleaning_dt),
        ("needs_cleaning", "cleaning", cleaning_dt),
        ("cleaning", "available", available_dt),
    ]

    for old_status, new_status, ts in transitions:
        db.execute(
            """
            INSERT INTO room_status_history
            (room_id, old_status, new_status, source, timestamp)
            VALUES (?, ?, ?, 'manual', ?)
            """,
            (room_id, old_status, new_status, ts.isoformat(sep=" ")),
        )


def test_visit_backed_metrics_and_filters():
    db = Database(":memory:")
    metrics = MetricsQueries(db)

    db.execute("INSERT INTO rooms (name, status) VALUES ('Exam A', 'available')")
    db.execute("INSERT INTO rooms (name, status) VALUES ('Exam B', 'available')")

    rooms = db.fetch_all("SELECT id FROM rooms ORDER BY id")
    room_a = rooms[0][0]
    room_b = rooms[1][0]

    _insert_visit_with_history(db, room_a, datetime(2026, 1, 1, 10, 0, 0), 300, 900, 240)
    _insert_visit_with_history(db, room_a, datetime(2026, 1, 1, 12, 0, 0), 600, 300, 120)
    _insert_visit_with_history(db, room_b, datetime(2026, 1, 1, 11, 0, 0), 120, 600, 180)

    assert metrics.avg_wait_time() == 340.0
    assert metrics.avg_provider_time() == 600.0
    assert metrics.avg_cleaning_time() == 180.0
    assert metrics.total_turnovers() == 3

    assert metrics.avg_wait_time("2026-01-01 11:00:00", "2026-01-01 12:30:00") == 360.0
    assert metrics.avg_provider_time("2026-01-01 11:00:00", "2026-01-01 12:30:00") == 450.0
    assert metrics.avg_cleaning_time("2026-01-01 11:00:00", "2026-01-01 12:30:00") == 150.0
    assert metrics.total_turnovers("2026-01-01 11:00:00", "2026-01-01 12:30:00") == 2

    db.close()


def test_stuck_rooms_only_returns_currently_stuck_ids():
    db = Database(":memory:")
    metrics = MetricsQueries(db)

    db.execute("INSERT INTO rooms (name, status) VALUES ('Exam A', 'needs_cleaning')")
    db.execute("INSERT INTO rooms (name, status) VALUES ('Exam B', 'needs_cleaning')")
    db.execute("INSERT INTO rooms (name, status) VALUES ('Exam C', 'available')")

    rooms = db.fetch_all("SELECT id FROM rooms ORDER BY id")
    room_a = rooms[0][0]
    room_b = rooms[1][0]
    room_c = rooms[2][0]

    old_ts = (datetime.now() - timedelta(seconds=4000)).isoformat(sep=" ")
    recent_ts = (datetime.now() - timedelta(seconds=60)).isoformat(sep=" ")

    db.execute(
        "INSERT INTO room_status_history (room_id, old_status, new_status, source, timestamp) VALUES (?, 'seeing_provider', 'needs_cleaning', 'manual', ?)",
        (room_a, old_ts),
    )
    db.execute(
        "INSERT INTO room_status_history (room_id, old_status, new_status, source, timestamp) VALUES (?, 'seeing_provider', 'needs_cleaning', 'manual', ?)",
        (room_b, recent_ts),
    )
    db.execute(
        "INSERT INTO room_status_history (room_id, old_status, new_status, source, timestamp) VALUES (?, 'cleaning', 'available', 'manual', ?)",
        (room_c, old_ts),
    )

    assert metrics.rooms_stuck_needing_cleaning(threshold_seconds=1800) == [room_a]

    db.close()