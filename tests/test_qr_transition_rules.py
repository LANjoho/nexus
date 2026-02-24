import pytest

from controllers.room_controller import RoomController
from database.db import Database
from models.enums import RoomStatus, UpdateSource
from services.transition_rules import allowed_targets_for_role


def test_role_targets_are_constrained_by_status():
    assert allowed_targets_for_role("patient", RoomStatus.AVAILABLE) == [RoomStatus.WAITING]
    assert allowed_targets_for_role("patient", RoomStatus.WAITING) == []
    assert allowed_targets_for_role("provider", RoomStatus.WAITING) == [RoomStatus.SEEING_PROVIDER]


def test_controller_rejects_invalid_transition():
    db = Database(":memory:")
    controller = RoomController(db)
    room_id = controller.create_room("Exam 1", RoomStatus.AVAILABLE)

    with pytest.raises(ValueError, match="Invalid transition"):
        controller.update_status(room_id, RoomStatus.CLEANING, UpdateSource.API)

    db.close()


def test_controller_allows_expected_transition():
    db = Database(":memory:")
    controller = RoomController(db)
    room_id = controller.create_room("Exam 2", RoomStatus.AVAILABLE)

    controller.update_status(room_id, RoomStatus.WAITING, UpdateSource.API)
    row = db.fetch_all("SELECT status FROM rooms WHERE id = ?", [room_id])[0]

    assert row[0] == RoomStatus.WAITING.value
    db.close()