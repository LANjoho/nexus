from datetime import datetime, timedelta
from database.db import Database
from models.enums import RoomStatus

db = Database()

# --- Clear tables ---
db.execute("DELETE FROM room_status_history")
db.execute("DELETE FROM rooms")

# --- Create Rooms ---
rooms = ["Exam 1", "Exam 2", "Exam 3", "Exam 4"]

for name in rooms:
    db.execute("INSERT INTO rooms (name, status) VALUES (?, ?)", 
               (name, RoomStatus.AVAILABLE.value))

# Fetch room IDs
room_rows = db.fetch_all("SELECT id, name FROM rooms")

now = datetime.now()

def log_transition(room_id, old, new, timestamp):
    db.execute(
        """
        INSERT INTO room_status_history
        (room_id, old_status, new_status, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (room_id, old, new, timestamp.isoformat())
    )

# --- Simulate Visits ---
durations = [
    (5, 12),   # Room 1: 5 min wait, 12 min provider
    (15, 20),  # Room 2
    (2, 8)     # Room 3
]

for i, (wait_min, provider_min) in enumerate(durations):
    room_id = room_rows[i]["id"]

    t0 = now - timedelta(hours=2, minutes=i*30)

    log_transition(room_id, "Available", "Waiting", t0)
    log_transition(room_id, "Waiting", "Seeing Provider", t0 + timedelta(minutes=wait_min))
    log_transition(room_id, "Seeing Provider", "Needs Cleaning",
                   t0 + timedelta(minutes=wait_min + provider_min))
    log_transition(room_id, "Needs Cleaning", "Cleaning",
                   t0 + timedelta(minutes=wait_min + provider_min + 5))
    log_transition(room_id, "Cleaning", "Available",
                   t0 + timedelta(minutes=wait_min + provider_min + 10))

# --- Add One Stuck Room (Exam 4) ---
stuck_room_id = room_rows[3]["id"]
t_stuck = now - timedelta(minutes=45)

log_transition(stuck_room_id, "Available", "Waiting", t_stuck)

print("Database seeded successfully.")
