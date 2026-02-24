import pytest

from scripts.generate_qr_assets import validate_base_url


def test_validate_base_url_rejects_unreachable_default_hosts():
    with pytest.raises(ValueError):
        validate_base_url("http://0.0.0.0:8787", allow_local_only=False)

    with pytest.raises(ValueError):
        validate_base_url("http://127.0.0.1:8787", allow_local_only=False)


def test_validate_base_url_accepts_local_when_opted_in():
    validate_base_url("http://127.0.0.1:8787", allow_local_only=True)


def test_validate_base_url_accepts_lan_ip():
    validate_base_url("http://192.168.1.50:8787", allow_local_only=False)