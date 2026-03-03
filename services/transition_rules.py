from models.enums import RoomStatus


ALL_STATUSES = set(RoomStatus)

# Demo/testing mode: allow any transition.
ALLOWED_TRANSITIONS = {
    status: set(ALL_STATUSES)
    for status in RoomStatus
}

# Demo/testing mode: patient and provider can choose any status.
ROLE_ALLOWED_TARGETS = {
    "patient": set(ALL_STATUSES),
    "provider": set(ALL_STATUSES),
}


def is_transition_allowed(old_status: RoomStatus, new_status: RoomStatus) -> bool:
    return new_status in ALLOWED_TRANSITIONS.get(old_status, set())


def allowed_targets_for_role(role: str, current_status: RoomStatus):
    role = role.lower()
    role_targets = ROLE_ALLOWED_TARGETS.get(role, set(ALL_STATUSES))
    return sorted(
        [status for status in role_targets if status != current_status],
        key=lambda s: s.value,
    )