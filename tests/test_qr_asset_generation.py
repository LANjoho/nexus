import os
import pytest

os.environ["NEXUS_QR_SECRET"] = "test-secret"

from scripts.generate_qr_assets import validate_base_url
from web.qr_server import create_shared_form_url


def test_validate_base_url_rejects_unreachable_default_hosts():
    with pytest.raises(ValueError):
        validate_base_url("http://0.0.0.0:8787", allow_local_only=False)

    with pytest.raises(ValueError):
        validate_base_url("http://127.0.0.1:8787", allow_local_only=False)


def test_validate_base_url_accepts_local_when_opted_in():
    validate_base_url("http://127.0.0.1:8787", allow_local_only=True)


def test_validate_base_url_accepts_lan_ip():
    validate_base_url("http://192.168.1.50:8787", allow_local_only=False)


def test_create_shared_form_url_uses_any_room_scope():
    url = create_shared_form_url("http://192.168.1.50:8787", "provider")
    assert "room_id=any" in url
    assert "role=provider" in url
    assert "sig=" in url