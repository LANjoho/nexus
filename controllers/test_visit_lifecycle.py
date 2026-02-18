from database.db import Database
from controllers.room_controller import RoomController
from models.enums import RoomStatus, UpdateSource

# Initialize DB + controller
db = Database("clinic.db")
controller = RoomController(db)

# 1️⃣ Create a room
room_id = controller.create_room("Test Room")
print(f"Created room with ID: {room_id}")

# 2️⃣ Run full lifecycle
controller.update_status(room_id, RoomStatus.WAITING)
controller.update_status(room_id, RoomStatus.SEEING_PROVIDER)
controller.update_status(room_id, RoomStatus.NEEDS_CLEANING)
controller.update_status(room_id, RoomStatus.CLEANING)
controller.update_status(room_id, RoomStatus.AVAILABLE)

print("Lifecycle completed.")

# 3️⃣ Check visits table
rows = db.fetch_all("SELECT * FROM visits")
for row in rows:
    print(dict(row))

db.close()
