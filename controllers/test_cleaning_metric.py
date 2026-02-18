import time
from database.db import Database
from controllers.room_controller import RoomController
from database.metrics_queries import MetricsQueries
from models.enums import RoomStatus

# Initialize DB + controllers
db = Database("clinic.db")
room_controller = RoomController(db)
metrics = MetricsQueries(db)

# Create unique room
room_id = room_controller.create_room(f"CleanTest-{time.time()}")
print(f"Created room {room_id}")

# Simulate lifecycle with delays
room_controller.update_status(room_id, RoomStatus.WAITING)
time.sleep(1)

room_controller.update_status(room_id, RoomStatus.SEEING_PROVIDER)
time.sleep(1)

room_controller.update_status(room_id, RoomStatus.NEEDS_CLEANING)
time.sleep(2)  # <-- this is the cleaning wait

room_controller.update_status(room_id, RoomStatus.CLEANING)
time.sleep(2)  # <-- active cleaning time

room_controller.update_status(room_id, RoomStatus.AVAILABLE)

print("Lifecycle complete.")

# Test avg cleaning time
avg_cleaning = metrics.avg_cleaning_time()
print(f"Average Cleaning Time (seconds): {avg_cleaning}")

print("ROOM STATUS HISTORY:")
rows = db.fetch_all("SELECT * FROM room_status_history")
for r in rows:
    print(dict(r))

db.close()
