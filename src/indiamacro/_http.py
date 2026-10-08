"""Shared HTTP layer: one session, retries, an on-disk cache and per-host quirks.

Quirks found while probing the sources (Oct 2026):
  * fred.stlouisfed.org resets connections for browser-like and unknown User-Agents,
    but accepts the default python-requests one.
  * www.imf.org (DataMapper) returns 403 for browser User-Agents.
  * api.mospi.gov.in needs TLS "unsafe legacy renegotiation", which OpenSSL 3 disables.
So we keep the stock python-requests User-Agent and enable legacy TLS for MoSPI only.
"""

from __future__ import annotations

import hashlib
import os
import ssl
import time
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CACHE_DIR = Path(os.environ.get("INDIAMACRO_CACHE", Path.home() / ".cache" / "indiamacro"))
DAY = 24 * 3600
FOREVER = None

_LEGACY_TLS_HOSTS = ("https://api.mospi.gov.in",)


class SourceError(RuntimeError):
    """A data source answered, but not with usable data."""

    def __init__(self, source: str, message: str):
        super().__init__(f"[{source}] {message}")
        self.source = source


class settings:
    """Global knobs. Example: ``indiamacro.settings.cache = False``."""

    cache: bool = os.environ.get("INDIAMACRO_NO_CACHE") is None
    timeout: float = 90.0


def _retry() -> Retry:
    return Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )


class _LegacyTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.mount("https://", HTTPAdapter(max_retries=_retry()))
        for host in _LEGACY_TLS_HOSTS:
            s.mount(host, _LegacyTLSAdapter(max_retries=_retry()))
        _session = s
    return _session


def _cache_path(url: str, params: dict | None) -> Path:
    full = url + ("?" + urlencode(sorted((params or {}).items()), doseq=True) if params else "")
    digest = hashlib.sha256(full.encode()).hexdigest()[:24]
    return CACHE_DIR / urlsplit(url).netloc / digest


def get(
    url: str,
    params: dict | None = None,
    *,
    ttl: float | None = DAY,
    source: str = "http",
    headers: dict | None = None,
) -> bytes:
    """GET ``url`` and return the body, serving from the disk cache when fresh.

    ``ttl`` is in seconds; ``None`` caches forever (use for versioned files such as PWT).
    """
    params = {k: v for k, v in (params or {}).items() if v is not None}
    path = _cache_path(url, params)
    if settings.cache and path.exists():
        age = time.time() - path.stat().st_mtime
        if ttl is None or age < ttl:
            return path.read_bytes()

    try:
        r = session().get(url, params=params, headers=headers, timeout=settings.timeout)
    except requests.RequestException as e:
        raise SourceError(source, f"request failed: {e}") from e
    if r.status_code >= 400:
        raise SourceError(source, f"HTTP {r.status_code} for {r.url}: {r.text[:200]}")

    if settings.cache:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(r.content)
        tmp.replace(path)
    return r.content


def get_json(url: str, params: dict | None = None, **kw):
    import json

    body = get(url, params, **kw)
    try:
        return json.loads(body)
    except ValueError as e:
        raise SourceError(kw.get("source", "http"), f"expected JSON from {url}, got: {body[:200]!r}") from e


def clear_cache() -> None:
    """Delete everything in the on-disk cache."""
    import shutil

    shutil.rmtree(CACHE_DIR, ignore_errors=True)
