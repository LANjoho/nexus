from database.db import Database
from controllers.room_controller import RoomController
from models.enums import RoomStatus

db = Database()
controller = RoomController(db)

# Add sample rooms
room_names = ["Room 101", "Room 102", "Room 103", "Room 104", "Room 105"]

for name in room_names:
    try:
        controller.create_room(name, initial_status=RoomStatus.AVAILABLE)
        print(f"Created {name}")
    except Exception as e:
        print(f"{name} already exists, skipping.")

db.close()

from database.db import Database

db = Database()
rows = db.conn.execute("SELECT * FROM room_events").fetchall()
for r in rows:
    print(dict(r))
db.close()
