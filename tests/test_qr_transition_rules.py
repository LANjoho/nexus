from controllers.room_controller import RoomController
from database.db import Database
from models.enums import RoomStatus, UpdateSource
from services.transition_rules import allowed_targets_for_role


def test_role_targets_include_all_statuses_for_demo():
    patient_targets = allowed_targets_for_role("patient", RoomStatus.AVAILABLE)
    provider_targets = allowed_targets_for_role("provider", RoomStatus.WAITING)

    assert RoomStatus.AVAILABLE not in patient_targets
    assert RoomStatus.WAITING not in provider_targets
    assert set(patient_targets) == {s for s in RoomStatus if s != RoomStatus.AVAILABLE}
    assert set(provider_targets) == {s for s in RoomStatus if s != RoomStatus.WAITING}


def test_controller_allows_previously_invalid_transition_in_demo_mode():
    db = Database(":memory:")
    controller = RoomController(db)
    room_id = controller.create_room("Exam 1", RoomStatus.AVAILABLE)

    controller.update_status(room_id, RoomStatus.CLEANING, UpdateSource.API)
    row = db.fetch_all("SELECT status FROM rooms WHERE id = ?", [room_id])[0]

    assert row[0] == RoomStatus.CLEANING.value
    db.close()