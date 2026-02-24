from models.enums import RoomStatus


ALLOWED_TRANSITIONS = {
    RoomStatus.AVAILABLE: {RoomStatus.WAITING, RoomStatus.MAINTENANCE, RoomStatus.OUT_OF_SERVICE},
    RoomStatus.WAITING: {RoomStatus.SEEING_PROVIDER, RoomStatus.MAINTENANCE, RoomStatus.OUT_OF_SERVICE},
    RoomStatus.SEEING_PROVIDER: {RoomStatus.NEEDS_CLEANING, RoomStatus.MAINTENANCE, RoomStatus.OUT_OF_SERVICE},
    RoomStatus.NEEDS_CLEANING: {RoomStatus.CLEANING, RoomStatus.MAINTENANCE, RoomStatus.OUT_OF_SERVICE},
    RoomStatus.CLEANING: {RoomStatus.AVAILABLE, RoomStatus.MAINTENANCE, RoomStatus.OUT_OF_SERVICE},
    RoomStatus.MAINTENANCE: {RoomStatus.AVAILABLE, RoomStatus.OUT_OF_SERVICE},
    RoomStatus.OUT_OF_SERVICE: {RoomStatus.AVAILABLE, RoomStatus.MAINTENANCE},
}


ROLE_ALLOWED_TARGETS = {
    "patient": {RoomStatus.WAITING},
    "provider": {RoomStatus.SEEING_PROVIDER, RoomStatus.NEEDS_CLEANING, RoomStatus.CLEANING, RoomStatus.AVAILABLE},
}


def is_transition_allowed(old_status: RoomStatus, new_status: RoomStatus) -> bool:
    if old_status == new_status:
        return True
    return new_status in ALLOWED_TRANSITIONS.get(old_status, set())


def allowed_targets_for_role(role: str, current_status: RoomStatus):
    role = role.lower()
    role_targets = ROLE_ALLOWED_TARGETS.get(role, set())
    return sorted(
        [status for status in role_targets if status != current_status and is_transition_allowed(current_status, status)],
        key=lambda s: s.value,
    )