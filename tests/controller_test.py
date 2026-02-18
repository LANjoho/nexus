from database.db import Database
from controllers.room_controller import RoomController
from models.enums import RoomStatus, UpdateSource

db = Database()
controller = RoomController(db)

# Create a room
room_id = controller.create_room("Room 101")
print(f"Created Room ID: {room_id}")

# Update status manually
controller.update_status(room_id, RoomStatus.SEEING_PROVIDER)
controller.update_status(room_id, RoomStatus.NEEDS_CLEANING)

# Fetch current rooms
rooms = controller.get_all_rooms()
for r in rooms:
    print(dict(r))

# Fetch events
events = controller.get_room_events(room_id)
for e in events:
    print(dict(e))
