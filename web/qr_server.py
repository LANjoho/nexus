import hashlib
import hmac
import os
import socket
from datetime import datetime
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from controllers.room_controller import RoomController
from database.db import Database
from models.enums import RoomStatus, UpdateSource
from services.shift_service import ShiftService
from services.transition_rules import allowed_targets_for_role


HOST = os.getenv("NEXUS_QR_HOST", "0.0.0.0")
PORT = int(os.getenv("NEXUS_QR_PORT", "8787"))
SECRET = os.getenv("NEXUS_QR_SECRET", "change-me")


def guess_reachable_host() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip:
                return ip
    except OSError:
        pass
    return "127.0.0.1"


def _sign(room_id: int, role: str) -> str:
    payload = f"{room_id}:{role.lower()}".encode("utf-8")
    return hmac.new(SECRET.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _verify(room_id: int, role: str, signature: str) -> bool:
    expected = _sign(room_id, role)
    return hmac.compare_digest(expected, signature)


def _active_db_path():
    service = ShiftService()
    active = service.get_active_db_path()
    return str(active) if active else "clinic.db"


class QRHandler(BaseHTTPRequestHandler):
    def _send_html(self, body: str, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def _render_form(self, room_id: int, role: str, signature: str):
        db = Database(_active_db_path())
        controller = RoomController(db)
        try:
            room = next((r for r in controller.get_all_rooms() if r["id"] == room_id), None)
            if not room:
                self._send_html("<h1>Room not found</h1>", 404)
                return

            current_status = RoomStatus(room["status"])
            allowed = allowed_targets_for_role(role, current_status)

            buttons = "".join(
                f'<button type="submit" name="new_status" value="{s.value}" style="padding: 14px; margin: 8px;">{s.value}</button>'
                for s in allowed
            )

            if not buttons:
                buttons = "<p>No valid actions available right now for this role.</p>"

            html = f"""
            <html>
              <body style=\"font-family: sans-serif; max-width: 640px; margin: 20px auto;\">
                <h1>Nexus Room Update</h1>
                <p><b>Room:</b> {escape(room['name'])} (id={room_id})</p>
                <p><b>Current status:</b> {escape(current_status.value)}</p>
                <p><b>Role:</b> {escape(role)}</p>
                <form method=\"post\" action=\"/update\">
                  <input type=\"hidden\" name=\"room_id\" value=\"{room_id}\" />
                  <input type=\"hidden\" name=\"role\" value=\"{escape(role)}\" />
                  <input type=\"hidden\" name=\"sig\" value=\"{escape(signature)}\" />
                  {buttons}
                </form>
              </body>
            </html>
            """
            self._send_html(html)
        finally:
            db.close()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_html("ok")
            return

        if parsed.path != "/form":
            self._send_html("<h1>Not Found</h1>", 404)
            return

        params = parse_qs(parsed.query)
        try:
            room_id = int(params.get("room_id", [""])[0])
            role = params.get("role", [""])[0].lower()
            sig = params.get("sig", [""])[0]
        except ValueError:
            self._send_html("<h1>Bad request</h1>", 400)
            return

        if role not in {"patient", "provider"}:
            self._send_html("<h1>Invalid role</h1>", 400)
            return

        if not _verify(room_id, role, sig):
            self._send_html("<h1>Invalid signature</h1>", 403)
            return

        self._render_form(room_id, role, sig)

    def do_POST(self):
        if self.path != "/update":
            self._send_html("<h1>Not Found</h1>", 404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        params = parse_qs(body)

        try:
            room_id = int(params.get("room_id", [""])[0])
            role = params.get("role", [""])[0].lower()
            sig = params.get("sig", [""])[0]
            new_status = RoomStatus(params.get("new_status", [""])[0])
        except (ValueError, KeyError):
            self._send_html("<h1>Bad request</h1>", 400)
            return

        if not _verify(room_id, role, sig):
            self._send_html("<h1>Invalid signature</h1>", 403)
            return

        db = Database(_active_db_path())
        controller = RoomController(db)
        try:
            room = next((r for r in controller.get_all_rooms() if r["id"] == room_id), None)
            if not room:
                self._send_html("<h1>Room not found</h1>", 404)
                return

            current_status = RoomStatus(room["status"])
            allowed = allowed_targets_for_role(role, current_status)
            if new_status not in allowed:
                self._send_html(
                    f"<h1>Rejected</h1><p>{escape(new_status.value)} is not allowed for role {escape(role)} from {escape(current_status.value)}.</p>",
                    400,
                )
                return

            controller.update_status(room_id, new_status, UpdateSource.API)
            self._send_html(
                f"<h1>Success</h1><p>Room {escape(room['name'])} updated to <b>{escape(new_status.value)}</b> at {datetime.now().isoformat(timespec='seconds')}.</p>"
            )
        except Exception as exc:
            self._send_html(f"<h1>Update failed</h1><p>{escape(str(exc))}</p>", 400)
        finally:
            db.close()


def create_signed_form_url(base_url: str, room_id: int, role: str) -> str:
    role = role.lower()
    sig = _sign(room_id, role)
    return f"{base_url.rstrip('/')}/form?room_id={room_id}&role={role}&sig={sig}"


def main():
    server = ThreadingHTTPServer((HOST, PORT), QRHandler)
    print(f"QR server running on http://{HOST}:{PORT}")
    if HOST == "0.0.0.0":
        print(f"Use this LAN URL in QR generation: http://{guess_reachable_host()}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()