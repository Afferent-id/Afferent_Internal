#!/usr/bin/env python3
"""Squid external ACL helper. Never logs the service credential."""

from __future__ import annotations

import json
import os
import sys
import socket
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import unquote


def secret(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    file_name = os.environ.get(f"{name}_FILE", "").strip()
    if file_name and Path(file_name).is_file():
        return Path(file_name).read_text(encoding="utf-8").strip()
    # Check common .env paths for standalone / homelab deployments
    candidates = [
        Path("/etc/afferent/.env"),
        Path("/home/flyingsundaman/Human_Firewall/.env"),
        Path(__file__).resolve().parent.parent / ".env",
        Path.cwd() / ".env"
    ]
    for cp in candidates:
        try:
            if cp.is_file():
                for line in cp.read_text(encoding="utf-8", errors="replace").splitlines():
                    line = line.strip()
                    if line.startswith(f"{name}="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""


def get_api_url() -> str:
    raw = os.environ.get("PROXY_DECISION_API_URL", "").strip()
    if not raw:
        raw = secret("PROXY_DECISION_API_URL")
    if not raw or "flask_api" in raw:
        # Check if flask_api is resolvable (Docker); if not, use localhost
        try:
            socket.gethostbyname("flask_api")
            return "http://flask_api:5000/api/proxy/decision"
        except socket.gaierror:
            return "http://127.0.0.1:5000/api/proxy/decision"
    return raw


API_URL = get_api_url()
TIMEOUT = float(os.environ.get("PROXY_DECISION_TIMEOUT_SECONDS", "2.5"))
FAIL_MODE = os.environ.get("PROXY_FAIL_MODE", "closed").strip().lower()
SERVICE_KEY = secret("SERVICE_API_KEY")

# Domains that are ALWAYS allowed without ML inspection.
# Add any service here that should never be intercepted by AFFERENT.
ALWAYS_ALLOW_DOMAINS: tuple[str, ...] = (
    # Discord
    "discord.com", "discordapp.com", "discord.gg", "discordapp.net",
    "discord.media", "gateway.discord.gg", "cdn.discordapp.com",
    "media.discordapp.net",
    # WhatsApp / Meta
    "whatsapp.com", "whatsapp.net",
    # Telegram
    "telegram.org", "t.me",
    # Slack
    "slack.com", "slack-edge.com",
    # Zoom
    "zoom.us", "zoom.com",
    # Microsoft / Windows Update
    "microsoft.com", "windows.com", "windowsupdate.com", "live.com",
    "office.com", "office365.com",
    # Apple / iCloud
    "apple.com", "icloud.com",
    # Google core
    "googleapis.com", "gstatic.com", "accounts.google.com",
    # CDN / infrastructure
    "cloudflare.com", "fastly.net", "akamai.net", "akamaized.net",
)


def _is_always_allowed(host: str) -> bool:
    """Return True if host matches any ALWAYS_ALLOW_DOMAINS entry."""
    host = host.lower().split(":")[0]
    for domain in ALWAYS_ALLOW_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return True
    return False


def local_fallback_decision(target: str) -> dict:
    """Evaluate domain locally using Stacker ML and whitelist if Flask API is unreachable."""
    host = target.split(":")[0].strip().lower()
    # 0. Hard-coded always-allow list (Discord, messaging apps, CDNs, etc.)
    if _is_always_allowed(host):
        return {"action": "allow", "domain": host, "reason": "Trusted service always-allow"}
    # 1. Whitelist / Trusted Domains Check
    try:
        import sys
        for p in ["/home/flyingsundaman/Human_Firewall/backend", str(Path(__file__).resolve().parent.parent / "backend")]:
            if p not in sys.path:
                sys.path.insert(0, p)
        from domain_reputation import check_domain_reputation
        rep = check_domain_reputation(f"https://{host}")
        if rep.get("trusted"):
            return {"action": "allow", "domain": host, "reason": rep.get("reason", "Trusted domain whitelist")}
    except Exception:
        pass

    # 2. Local Stacker XGBoost ML Scanner
    try:
        from services import stacker_scanner
        stacker_scanner.warmup()
        res = stacker_scanner.scan(host)
        if res.get("verdict") == "malicious":
            return {"action": "block", "domain": host, "reason": res.get("reason", "Malicious threat detected")}
        else:
            return {"action": "allow", "domain": host, "reason": res.get("reason", "Clean domain")}
    except Exception:
        pass

    return {"action": "allow", "domain": host, "reason": "Default allow fallback"}


def decision(client_ip: str, method: str, target: str) -> dict:
    # Short-circuit for always-allowed services before hitting Flask API
    if _is_always_allowed(target):
        return {"action": "allow", "domain": target.split(":")[0].lower(), "reason": "Trusted service always-allow"}
    event_id = str(uuid.uuid4())
    port = None
    if method.upper() == "CONNECT" and ":" in target:
        maybe_port = target.rsplit(":", 1)[-1]
        if maybe_port.isdigit():
            port = int(maybe_port)
    payload = json.dumps(
        {
            "schemaVersion": "1.0",
            "eventId": event_id,
            "requestId": event_id,
            "clientIp": client_ip,
            "method": method,
            "target": target,
            "port": port,
        },
        separators=(",", ":"),
    ).encode()
    request = urllib.request.Request(
        API_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {SERVICE_KEY}",
            "Content-Type": "application/json",
            "X-Request-ID": event_id,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("action") not in {"allow", "block"} or not result.get("domain"):
            raise ValueError("Invalid proxy decision response")
        return result
    except Exception:
        # Fallback to local in-process ML and whitelist evaluation
        return local_fallback_decision(target)


def clean_message(value: str) -> str:
    return " ".join(value.replace('"', "'").replace("\r", " ").replace("\n", " ").split())[:180]


def register_allowed_tunnel(client_ip, client_port, domain, started):
    sock_path = "/run/afferent/allow.sock"
    if not os.path.exists(sock_path):
        return  # Standalone mode without tunnel relay
    payload = {"clientIp": client_ip, "clientPort": int(client_port), "domain": domain, "started": started}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as control:
            control.settimeout(0.5)
            control.connect(sock_path)
            control.sendall(json.dumps(payload).encode() + b"\n")
            control.recv(16)
    except Exception:
        pass


def main():
    global SERVICE_KEY, API_URL
    if not SERVICE_KEY:
        SERVICE_KEY = secret("SERVICE_API_KEY")
    if not SERVICE_KEY:
        print("WARNING: AFFERENT proxy helper running without SERVICE_API_KEY; check .env", file=sys.stderr, flush=True)
    for raw_line in sys.stdin:
        # Squid appends an optional %DATA token; decode each URL-escaped field
        # once, never log request headers, cookies, or the bearer credential.
        parts = [unquote(part) for part in raw_line.strip().split()[:6]]
        if len(parts) != 6:
            print('OK message="Invalid proxy request"', flush=True)
            continue
        client_ip, client_port, local_ip, local_port, method, target = parts
        try:
            started = time.monotonic()
            result = decision(client_ip, method, target)
            if result["action"] == "block":
                print(f'OK message="{clean_message(str(result.get("reason", "AFFERENT policy")))}"', flush=True)
            else:
                if method.upper() == "CONNECT":
                    register_allowed_tunnel(client_ip, client_port, result["domain"], started)
                print("ERR", flush=True)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            print(f"AFFERENT decision API error: {type(exc).__name__}", file=sys.stderr, flush=True)
            if FAIL_MODE == "open":
                print("ERR", flush=True)
            else:
                print('OK message="AFFERENT security service unavailable"', flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

