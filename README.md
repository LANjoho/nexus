Nexus is a clinical room management software for healthcare providers.

## QR-driven room updates (local-first prototype)

You can run a lightweight local web server so phones can scan room QR codes and submit status updates.

### 1) Start the QR update server

```bash
NEXUS_QR_SECRET='replace-with-strong-secret' python -m web.qr_server
```

Optional environment variables:
- `NEXUS_QR_HOST` (default `0.0.0.0`)
- `NEXUS_QR_PORT` (default `8787`)
- `NEXUS_QR_SECRET` (used to sign QR URLs)

> If host is `0.0.0.0`, the server listens on all interfaces. That is **not** a scannable QR host value.
> Use your laptop LAN IP (example: `http://192.168.1.50:8787`) when generating QR links.

### 2) Generate patient/provider URLs and QR assets

```bash
NEXUS_QR_SECRET='replace-with-strong-secret' python scripts/generate_qr_assets.py --base-url http://192.168.1.50:8787
```

If you omit `--base-url`, the script tries to auto-detect a reachable LAN host.

```bash
NEXUS_QR_SECRET='replace-with-strong-secret' python scripts/generate_qr_assets.py
```

For laptop-only testing (not phone-scannable), you can explicitly allow localhost:

```bash
python scripts/generate_qr_assets.py --base-url http://127.0.0.1:8787 --allow-local-only
```

This creates `artifacts/qr/qr_urls.csv` and, if `qrcode[pil]` is installed, one PNG QR image per room/role.

### 3) Scan from phones

Phones must be able to reach `http://<host-ip>:8787` over the same network.

Notes:
- Patient and provider flows are separated.
- Role and transition checks are enforced server-side.
- Updates are recorded with source `api`.