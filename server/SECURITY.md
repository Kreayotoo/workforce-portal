# Security & Compliance — Amaravati Digital Twin Server

## What is enforced (out of the box)
- **Login required** (`security.json → require_auth: true`). Seeded account **admin / admin123 — change immediately** via `POST /api/auth/password`.
- **Signed session tokens** (HMAC-SHA256, server-side secret auto-generated in `secret.key`), expiry 8 h (`token_hours`).
- **Password storage:** PBKDF2-HMAC-SHA256, 120,000 iterations, per-user salt. No plaintext anywhere.
- **RBAC roles:** Admin · Engineer · Operator · Viewer. O&M writes need Operator+; user management & audit need Admin; Viewer is read-only (also enforced in the app UI).
- **Audit trail:** every login/failure, password change, user add/delete and O&M write appended to `audit.log` (UTC, user, IP, action). `GET /api/audit` (Admin) returns the last 200 events.
- **Backups:** `om_store.json` snapshotted to `backups/` at most every 6 h on write; last 30 kept.
- **CORS allow-list** in `security.json` (default: local + `null` for the offline app file). Add your LAN origin, e.g. `"http://10.0.0.5:8000"`.

## HTTPS deployment (recommended for any multi-user use)
1. `pip install uvicorn fastapi aiofiles httpx`
2. Obtain a certificate (internal CA or Let's Encrypt via reverse proxy).
3. Simplest: run behind **nginx/caddy** with TLS terminating at the proxy → `proxy_pass http://127.0.0.1:8000;`
4. Or direct: `uvicorn main:app --host 0.0.0.0 --port 8443 --ssl-keyfile key.pem --ssl-certfile cert.pem`
5. Update `allow_origins` accordingly and change the app's server URL list if a non-default host is used.

## Control mapping (indicative)
| Control area | ISO 27001:2022 | CERT-In / GoI guidance | Implementation here |
|---|---|---|---|
| Access control / least privilege | A.5.15, A.8.2 | Role-based access | 4 RBAC roles, endpoint gating |
| Authentication | A.5.17 | Strong auth | PBKDF2 passwords, signed expiring tokens |
| Logging & monitoring | A.8.15 | 180-day log retention advisory | audit.log (rotate/retain per policy) |
| Backup | A.8.13 | Regular backups | 6-hourly store snapshots, 30 kept |
| Cryptography | A.8.24 | Approved algorithms | SHA-256 HMAC, PBKDF2 |
| Secure transfer | A.8.20/21 | TLS in transit | HTTPS guide above |
| Data sovereignty | — | Data localisation | Fully on-premise; zero external cloud |

*Honest note:* this is an engineering implementation of the controls, not a certification. Formal ISO/CERT-In audit is an organisational exercise; this document is written to make that audit straightforward.
