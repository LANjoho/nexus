"""Seed realistic fake room lifecycle data for metrics validation.

Usage examples:
  python tests/seed_metrics_data.py
  python tests/seed_metrics_data.py --db clinic.db --rooms 12 --days 14 --cycles 8 --stuck 2 --reset
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from database.db import Database
from models.enums import RoomStatus, UpdateSource

@dataclass
class SeedConfig:
    db_path: str = "clinic.db"
    room_count: int = 10
    days_back: int = 10
    cycles_per_room: int = 6
    stuck_rooms: int = 2
    reset: bool = False
    seed: int = 42


def _insert_transition(db: Database, room_id: int, old: RoomStatus, new: RoomStatus, ts: datetime):
    payload = (room_id, old.value, new.value, UpdateSource.MANUAL.value, ts.isoformat(sep=" "))

    db.execute(
        """
        INSERT INTO room_status_history (room_id, old_status, new_status, source, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        payload,
    )

    db.execute(
        """
        INSERT INTO room_events (room_id, old_status, new_status, source, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        payload,
    )


def _insert_completed_visit(db: Database, room_id: int, start_ts: datetime):
    wait_s = random.randint(2 * 60, 20 * 60)
    provider_s = random.randint(8 * 60, 35 * 60)
    needs_cleaning_wait_s = random.randint(1 * 60, 12 * 60)
    cleaning_s = random.randint(3 * 60, 18 * 60)
    
    waiting_ts = start_ts
    seeing_provider_ts = waiting_ts + timedelta(seconds=wait_s)
    needs_cleaning_ts = seeing_provider_ts + timedelta(seconds=provider_s)
    cleaning_ts = needs_cleaning_ts + timedelta(seconds=needs_cleaning_wait_s)
    available_ts = cleaning_ts + timedelta(seconds=cleaning_s)

    db.execute(
        "INSERT INTO visits (room_id, start_time, end_time) VALUES (?, ?, ?)",
        (room_id, waiting_ts.isoformat(sep=" "), available_ts.isoformat(sep=" ")),
    )

    _insert_transition(db, room_id, RoomStatus.AVAILABLE, RoomStatus.WAITING, waiting_ts)
    _insert_transition(db, room_id, RoomStatus.WAITING, RoomStatus.SEEING_PROVIDER, seeing_provider_ts)
    _insert_transition(db, room_id, RoomStatus.SEEING_PROVIDER, RoomStatus.NEEDS_CLEANING, needs_cleaning_ts)
    _insert_transition(db, room_id, RoomStatus.NEEDS_CLEANING, RoomStatus.CLEANING, cleaning_ts)
    _insert_transition(db, room_id, RoomStatus.CLEANING, RoomStatus.AVAILABLE, available_ts)

    return available_ts


def _insert_stuck_visit(db: Database, room_id: int, start_ts: datetime):
    wait_s = random.randint(2 * 60, 12 * 60)
    provider_s = random.randint(10 * 60, 25 * 60)
    stuck_age_s = random.randint(35 * 60, 90 * 60)

    waiting_ts = start_ts
    seeing_provider_ts = waiting_ts + timedelta(seconds=wait_s)
    needs_cleaning_ts = seeing_provider_ts + timedelta(seconds=provider_s)

    # keep this room currently stuck
    now = datetime.now()
    if now - needs_cleaning_ts < timedelta(seconds=stuck_age_s):
        needs_cleaning_ts = now - timedelta(seconds=stuck_age_s)

    db.execute(
        "INSERT INTO visits (room_id, start_time, end_time) VALUES (?, ?, NULL)",
        (room_id, waiting_ts.isoformat(sep=" "),),
    )

    _insert_transition(db, room_id, RoomStatus.AVAILABLE, RoomStatus.WAITING, waiting_ts)
    _insert_transition(db, room_id, RoomStatus.WAITING, RoomStatus.SEEING_PROVIDER, seeing_provider_ts)
    _insert_transition(db, room_id, RoomStatus.SEEING_PROVIDER, RoomStatus.NEEDS_CLEANING, needs_cleaning_ts)

    db.execute("UPDATE rooms SET status = ? WHERE id = ?", (RoomStatus.NEEDS_CLEANING.value, room_id))


def seed_fake_metrics(config: SeedConfig):
    random.seed(config.seed)
    db = Database(config.db_path)

    if config.reset:
        db.execute("DELETE FROM room_events")
        db.execute("DELETE FROM room_status_history")
        db.execute("DELETE FROM visits")
        db.execute("DELETE FROM rooms")

    existing = db.fetch_all("SELECT id, name FROM rooms ORDER BY id")
    if len(existing) < config.room_count:
        for i in range(len(existing), config.room_count):
            db.execute(
                "INSERT INTO rooms (name, status) VALUES (?, ?)",
                (f"Exam {i+1:02d}", RoomStatus.AVAILABLE.value),
            )

    rooms = db.fetch_all("SELECT id FROM rooms ORDER BY id LIMIT ?", [config.room_count])
    room_ids = [row[0] for row in rooms]

    base_start = datetime.now() - timedelta(days=config.days_back)

    for room_id in room_ids:
        current = base_start + timedelta(minutes=random.randint(0, 120))

        for _ in range(config.cycles_per_room):
            current = _insert_completed_visit(db, room_id, current)
            current += timedelta(minutes=random.randint(10, 90))

    # mark some rooms as actively stuck in needs_cleaning
    for room_id in room_ids[: min(config.stuck_rooms, len(room_ids))]:
        stuck_start = datetime.now() - timedelta(hours=random.randint(2, 8))
        _insert_stuck_visit(db, room_id, stuck_start)

    summary = {
        "rooms": db.fetch_one("SELECT COUNT(*) FROM rooms"),
        "visits": db.fetch_one("SELECT COUNT(*) FROM visits"),
        "history_rows": db.fetch_one("SELECT COUNT(*) FROM room_status_history"),
        "event_rows": db.fetch_one("SELECT COUNT(*) FROM room_events"),
        "stuck_rooms": db.fetch_one("SELECT COUNT(*) FROM rooms WHERE status='needs_cleaning'"),
    }

    db.close()
    return summary


def parse_args() -> SeedConfig:
    parser = argparse.ArgumentParser(description="Seed fake lifecycle data for metrics")
    parser.add_argument("--db", default="clinic.db", help="SQLite DB path")
    parser.add_argument("--rooms", type=int, default=10, help="How many rooms to seed")
    parser.add_argument("--days", type=int, default=10, help="How far back to start generating visits")
    parser.add_argument("--cycles", type=int, default=6, help="Completed cycles per room")
    parser.add_argument("--stuck", type=int, default=2, help="How many rooms should end in needs_cleaning")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible fake data")
    parser.add_argument("--reset", action="store_true", help="Clear tables before seeding")
    args = parser.parse_args()

    return SeedConfig(
        db_path=args.db,
        room_count=args.rooms,
        days_back=args.days,
        cycles_per_room=args.cycles,
        stuck_rooms=args.stuck,
        reset=args.reset,
        seed=args.seed,
    )

if __name__ == "__main__":
    result = seed_fake_metrics(parse_args())
    print("Fake metrics data seeded:")
    for key, value in result.items():
        print(f"  - {key}: {value}")