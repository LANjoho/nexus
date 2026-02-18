from models.enums import RoomStatus, UpdateSource
from database.db import Database
from datetime import datetime

class RoomController:
    """
    Core logic for managing rooms.
    All room status changes go through this class.
    """

    def __init__(self, db: Database):
        self.db = db

    # ---------------------------
    # Room creation
    # ---------------------------
    def create_room(self, name: str, initial_status=RoomStatus.AVAILABLE):
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT INTO rooms (name, status) VALUES (?, ?)",
            (name, initial_status.value),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    # ---------------------------
    # Update room status
    # ---------------------------
    def update_status(
        self,
        room_id: int,
        new_status: RoomStatus,
        source: UpdateSource = UpdateSource.MANUAL,
    ):
        cursor = self.db.conn.cursor()

        # Get current status
        row = cursor.execute(
            "SELECT status FROM rooms WHERE id=?", (room_id,)
        ).fetchone()

        if not row:
            raise ValueError(f"Room with ID {room_id} does not exist")

        old_status = row["status"]

        # ---------------------------
        # VISIT START LOGIC
        # ---------------------------
        if (
            old_status == RoomStatus.AVAILABLE.value
            and new_status == RoomStatus.WAITING
        ):
            # Check for existing active visit
            active_visit = cursor.execute(
                """
                SELECT id FROM visits
                WHERE room_id = ?
                AND end_time IS NULL
                """,
                (room_id,),
            ).fetchone()

            if not active_visit:
                cursor.execute(
                    """
                    INSERT INTO visits (room_id, start_time)
                    VALUES (?, ?)
                    """,
                    (room_id, datetime.now()),
                )

        # ---------------------------
        # VISIT END LOGIC
        # ---------------------------
        if (
            old_status == RoomStatus.CLEANING.value
            and new_status == RoomStatus.AVAILABLE
        ):
            cursor.execute(
                """
                UPDATE visits
                SET end_time = ?
                WHERE room_id = ?
                AND end_time IS NULL
                """,
                (datetime.now(), room_id),
            )

        # ---------------------------
        # Update rooms table
        # ---------------------------
        cursor.execute(
            "UPDATE rooms SET status=? WHERE id=?",
            (new_status.value, room_id),
        )

        # ---------------------------
        # Log the change
        # ---------------------------
        cursor.execute(
            """
            INSERT INTO room_events (room_id, old_status, new_status, source)
            VALUES (?, ?, ?, ?)
            """,
            (room_id, old_status, new_status.value, source.value),
        )
        
        # Log into room_status_history (used for metrics)
        cursor.execute(
            """
            INSERT INTO room_status_history (room_id, old_status, new_status, source)
            VALUES (?, ?, ?, ?)
            """,
            (room_id, old_status, new_status.value, source.value),
        )


        self.db.conn.commit()


    # ---------------------------
    # Query methods
    # ---------------------------
    def get_all_rooms(self):
        cursor = self.db.conn.cursor()
        rows = cursor.execute("SELECT * FROM rooms").fetchall()
        return rows

    def get_room_events(self, room_id: int):
        cursor = self.db.conn.cursor()
        rows = cursor.execute(
            "SELECT * FROM room_events WHERE room_id=? ORDER BY timestamp DESC",
            (room_id,),
        ).fetchall()
        return rows
