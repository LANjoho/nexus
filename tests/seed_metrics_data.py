import random
from datetime import datetime, timedelta

from database.db import Database
from models.enums import RoomStatus, UpdateSource
from controllers.room_controller import RoomController

db = Database()
controller = RoomController(db)

ROOM_STATUSES_FLOW = [
    RoomStatus.AVAILABLE,
    RoomStatus.OCCUPIED,
    RoomStatus.NEEDS_CLEANING,
    RoomStatus.CLEANING,
    RoomStatus.AVAILABLE
]

def seed_fake_metrics(days=7, cycles_per_room=5):
    rooms = controller.get_all_rooms()
    now = datetime.now()

    for room in rooms:
        current_time = now - timedelta(days=days)

        for _ in range(cycles_per_room):
            for i in range(len(ROOM_STATUSES_FLOW) - 1):
                old = ROOM_STATUSES_FLOW[i]
                new = ROOM_STATUSES_FLOW[i + 1]

                # Random but realistic durations
                if new == RoomStatus.OCCUPIED:
                    delta = timedelta(minutes=random.randint(30, 180))
                elif new == RoomStatus.NEEDS_CLEANING:
                    delta = timedelta(minutes=random.randint(10, 30))
                elif new == RoomStatus.CLEANING:
                    delta = timedelta(minutes=random.randint(5, 20))
                else:
                    delta = timedelta(minutes=random.randint(5, 15))

                current_time += delta

                db.execute(
                    """
                    INSERT INTO room_status_history
                    (room_id, old_status, new_status, source, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        room["id"],
                        old.value,
                        new.value,
                        UpdateSource.MANUAL.value,
                        current_time.isoformat()
                    )
                )

    print("Fake metrics data seeded.")

if __name__ == "__main__":
    seed_fake_metrics()
