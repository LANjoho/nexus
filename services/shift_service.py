from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ShiftInfo:
    start_time: datetime
    db_path: Path


class ShiftService:
    """Manage per-shift SQLite database files."""

    def __init__(self, base_dir="data/shifts", active_file="data/active_shift.txt"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.active_file = Path(active_file)
        self.active_file.parent.mkdir(parents=True, exist_ok=True)

    def get_active_db_path(self):
        if self.active_file.exists():
            raw = self.active_file.read_text(encoding="utf-8").strip()
            if raw:
                return Path(raw)
        return None

    def start_shift(self):
        active = self.get_active_db_path()
        if active and active.exists():
            return active, False

        now = datetime.now()
        db_path = self.base_dir / f"clinic_shift_{now.strftime('%Y%m%d_%H%M%S')}.db"
        self.active_file.write_text(str(db_path), encoding="utf-8")
        return db_path, True

    def end_shift(self):
        active = self.get_active_db_path()
        if not active:
            return None, None, False

        end_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        archived = active.with_name(f"{active.stem}_ended_{end_tag}{active.suffix}")

        if active.exists():
            active.rename(archived)
        else:
            archived = active

        if self.active_file.exists():
            self.active_file.unlink()

        return active, archived, True