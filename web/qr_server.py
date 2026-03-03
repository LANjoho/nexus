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


HOST = os.getenv("NEXUS_QR_HOST", "0.0.0.0")
PORT = int(os.getenv("NEXUS_QR_PORT", "8787"))
SECRET = os.getenv("NEXUS_QR_SECRET", "change-me")

ANY_ROOM_SCOPE = "any"


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


def _sign(scope: str, role: str) -> str:
    payload = f"{scope}:{role.lower()}".encode("utf-8")
    return hmac.new(SECRET.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _verify(scope: str, role: str, signature: str) -> bool:
    expected = _sign(scope, role)
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

    def _render_single_room_form(self, room, role: str, signature: str):
        current_status = RoomStatus(room["status"])
        buttons = "".join(
            f'<button type="submit" name="new_status" value="{s.value}" style="padding: 14px; margin: 8px;">{s.value}</button>'
            for s in RoomStatus
            if s.value != current_status.value
        )

        html = f"""
        <html>
          <body style=\"font-family: sans-serif; max-width: 900px; margin: 20px auto;\">
            <h1>Nexus Room Update</h1>
            <p><b>Room:</b> {escape(room['name'])} (id={room['id']})</p>
            <p><b>Current status:</b> {escape(current_status.value)}</p>
            <p><b>Role:</b> {escape(role)}</p>
            <form method=\"post\" action=\"/update\">
              <input type=\"hidden\" name=\"scope\" value=\"{room['id']}\" />
              <input type=\"hidden\" name=\"room_id\" value=\"{room['id']}\" />
              <input type=\"hidden\" name=\"role\" value=\"{escape(role)}\" />
              <input type=\"hidden\" name=\"sig\" value=\"{escape(signature)}\" />
              {buttons}
            </form>
          </body>
        </html>
        """
        self._send_html(html)

    def _render_multi_room_form(self, rooms, role: str, signature: str):
        room_options = "".join(
            f'<option value="{room["id"]}">{escape(room["name"])}</option>'
            for room in rooms
        )
        status_options = "".join(
            f'<option value="{status.value}">{escape(status.value)}</option>'
            for status in RoomStatus
        )

        html = f"""
        <html>
          <body style=\"font-family: sans-serif; max-width: 900px; margin: 20px auto;\">
            <h1>Nexus Room Update</h1>
            <p><b>Role:</b> {escape(role)}</p>
            <p>Demo mode: choose any room and any status.</p>
            <form method=\"post\" action=\"/update\">
              <input type=\"hidden\" name=\"scope\" value=\"{ANY_ROOM_SCOPE}\" />
              <input type=\"hidden\" name=\"role\" value=\"{escape(role)}\" />
              <input type=\"hidden\" name=\"sig\" value=\"{escape(signature)}\" />

              <label for=\"room_id\"><b>Room</b></label><br />
              <select name=\"room_id\" id=\"room_id\" style=\"padding: 10px; margin: 8px 0 16px 0; min-width: 260px;\">
                {room_options}
              </select><br />

              <label for=\"new_status\"><b>Status</b></label><br />
              <select name=\"new_status\" id=\"new_status\" style=\"padding: 10px; margin: 8px 0 16px 0; min-width: 260px;\">
                {status_options}
              </select><br />

              <button type=\"submit\" style=\"padding: 12px 20px;\">Update Room</button>
            </form>
          </body>
        </html>
        """
        self._send_html(html)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_html("ok")
            return

        if parsed.path != "/form":
            self._send_html("<h1>Not Found</h1>", 404)
            return

        params = parse_qs(parsed.query)
        role = params.get("role", [""])[0].lower()
        scope = params.get("room_id", [ANY_ROOM_SCOPE])[0]
        sig = params.get("sig", [""])[0]

        if role not in {"patient", "provider"}:
            self._send_html("<h1>Invalid role</h1>", 400)
            return

        if not _verify(scope, role, sig):
            self._send_html("<h1>Invalid signature</h1>", 403)
            return

        db = Database(_active_db_path())
        controller = RoomController(db)
        try:
            rooms = sorted(controller.get_all_rooms(), key=lambda r: r["name"].lower())
            if not rooms:
                self._send_html("<h1>No rooms configured</h1>", 400)
                return

            if scope == ANY_ROOM_SCOPE:
                self._render_multi_room_form(rooms, role, sig)
                return

            try:
                room_id = int(scope)
            except ValueError:
                self._send_html("<h1>Bad request</h1>", 400)
                return

            room = next((r for r in rooms if r["id"] == room_id), None)
            if not room:
                self._send_html("<h1>Room not found</h1>", 404)
                return

            self._render_single_room_form(room, role, sig)
        finally:
            db.close()

    def do_POST(self):
        if self.path != "/update":
            self._send_html("<h1>Not Found</h1>", 404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        params = parse_qs(body)

        try:
            scope = params.get("scope", [ANY_ROOM_SCOPE])[0]
            room_id = int(params.get("room_id", [""])[0])
            role = params.get("role", [""])[0].lower()
            sig = params.get("sig", [""])[0]
            new_status = RoomStatus(params.get("new_status", [""])[0])
        except (ValueError, KeyError):
            self._send_html("<h1>Bad request</h1>", 400)
            return

        if role not in {"patient", "provider"}:
            self._send_html("<h1>Invalid role</h1>", 400)
            return

        if scope != ANY_ROOM_SCOPE and scope != str(room_id):
            self._send_html("<h1>Bad request</h1><p>Mismatched room scope.</p>", 400)
            return

        if not _verify(scope, role, sig):
            self._send_html("<h1>Invalid signature</h1>", 403)
            return

        db = Database(_active_db_path())
        controller = RoomController(db)
        try:
            room = next((r for r in controller.get_all_rooms() if r["id"] == room_id), None)
            if not room:
                self._send_html("<h1>Room not found</h1>", 404)
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
    scope = str(room_id)
    sig = _sign(scope, role)
    return f"{base_url.rstrip('/')}/form?room_id={scope}&role={role}&sig={sig}"


def create_shared_form_url(base_url: str, role: str) -> str:
    role = role.lower()
    sig = _sign(ANY_ROOM_SCOPE, role)
    return f"{base_url.rstrip('/')}/form?room_id={ANY_ROOM_SCOPE}&role={role}&sig={sig}"


def main():
    server = ThreadingHTTPServer((HOST, PORT), QRHandler)
    print(f"QR server running on http://{HOST}:{PORT}")
    if HOST == "0.0.0.0":
        print(f"Use this LAN URL in QR generation: http://{guess_reachable_host()}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()