import argparse
import csv
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db import Database
from services.shift_service import ShiftService
from web.qr_server import create_signed_form_url, guess_reachable_host


DISALLOWED_QR_HOSTS = {"0.0.0.0", "127.0.0.1", "localhost"}


def _active_db_path():
    active = ShiftService().get_active_db_path()
    return str(active) if active else "clinic.db"


def validate_base_url(base_url: str, allow_local_only: bool):
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Base URL must begin with http:// or https://")
    if not parsed.netloc:
        raise ValueError("Base URL must include host (and optional port)")

    host = (parsed.hostname or "").lower()
    if not allow_local_only and host in DISALLOWED_QR_HOSTS:
        raise ValueError(
            "Base URL host cannot be 0.0.0.0/127.0.0.1/localhost for phone-scannable QR codes. "
            "Use your LAN IP (for example: http://192.168.1.50:8787) or pass --allow-local-only for laptop-only testing."
        )


def main():
    parser = argparse.ArgumentParser(description="Generate signed QR form URLs for room-role pairs.")
    parser.add_argument("--base-url", help="Base URL for QR form endpoint, e.g., http://192.168.1.100:8787")
    parser.add_argument("--allow-local-only", action="store_true", help="Allow localhost/127.0.0.1 base URL for non-phone local testing")
    parser.add_argument("--output-dir", default="artifacts/qr", help="Directory for CSV and optional images")
    args = parser.parse_args()

    base_url = args.base_url
    if not base_url:
        reachable_host = guess_reachable_host()
        base_url = f"http://{reachable_host}:8787"
        print(f"No --base-url provided. Using detected host: {base_url}")

    validate_base_url(base_url, args.allow_local_only)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    db = Database(_active_db_path())
    rooms = db.fetch_all("SELECT id, name FROM rooms ORDER BY name")
    db.close()

    csv_path = output_dir / "qr_urls.csv"
    rows = []
    for room in rooms:
        for role in ("patient", "provider"):
            url = create_signed_form_url(base_url, room["id"], role)
            rows.append({"room_id": room["id"], "room_name": room["name"], "role": role, "url": url})

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["room_id", "room_name", "role", "url"])
        writer.writeheader()
        writer.writerows(rows)

    try:
        import qrcode  # type: ignore

        for row in rows:
            filename = f"room_{row['room_id']}_{row['role']}.png"
            img = qrcode.make(row["url"])
            img.save(output_dir / filename)
        print(f"Wrote CSV and QR PNGs to {output_dir}")
    except ImportError:
        print(f"Wrote CSV to {csv_path}. Install 'qrcode[pil]' to also render PNG files.")


if __name__ == "__main__":
    main()