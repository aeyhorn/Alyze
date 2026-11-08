"""SAP Business One Service Layer HTTP client.

Responsibilities
----------------
* Session management  – POST /Login, B1SESSION + ROUTEID cookies
* CSRF handling       – X-CSRF-Token: Fetch, cached per session
* 401 auto-retry      – discard session, re-login, retry once
* DRY_RUN guard       – blocks POST/PATCH/PUT/DELETE when SL_DRY_RUN=true
* Mode switching      – dev ↔ prod forces a fresh session + SQL-pool rebuild

This module is WRITE-channel only.  All reads go through MSSQL (db/sap.py).
"""

from __future__ import annotations

import threading
import time
from typing import Any

import httpx
import structlog

from bdx.config import SapMode, ServiceLayerSettings

logger = structlog.get_logger(__name__)

_WRITE_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})
_SESSION_TTL_SECONDS = 20 * 60  # SAP internal session lifetime
_SESSION_REFRESH_BUFFER = 30  # renew this many seconds before expiry


class ServiceLayerError(Exception):
    """Raised when the Service Layer returns HTTP ≥ 400."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class DryRunError(Exception):
    """Raised when a write is attempted while DRY_RUN is active."""


class ServiceLayerClient:
    """Thread-safe Service Layer HTTP client.

    Usage
    -----
    client = ServiceLayerClient(settings, mode=SapMode.DEV)
    data   = client.sl_call("GET", "ProductionOrders", params={"$top": "5"})
    client.sl_call("PATCH", f"ProductionOrders({doc_entry})", body={...})
    client.logout()
    """

    def __init__(self, settings: ServiceLayerSettings, mode: SapMode = SapMode.DEV) -> None:
        self._cfg = settings
        self._mode = mode
        self._lock = threading.Lock()

        # Session state
        self._cookies: dict[str, str] = {}
        self._csrf_token: str = ""
        self._session_expires_at: float = 0.0
        self._company_db: str = ""

        self._http = self._build_http_client()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def mode(self) -> SapMode:
        return self._mode

    @property
    def company_db(self) -> str:
        return self._cfg.company_db_for_mode(self._mode)

    @property
    def configured(self) -> bool:
        return self._cfg.configured

    @property
    def dry_run(self) -> bool:
        return self._cfg.dry_run

    @property
    def write_enabled(self) -> bool:
        return self._cfg.write_enabled

    def switch_mode(self, mode: SapMode) -> None:
        """Switch dev/prod mode.  Clears the current session immediately."""
        with self._lock:
            if mode == self._mode:
                return
            logger.info("service_layer.mode_switch", old=self._mode, new=mode)
            self._mode = mode
            self._clear_session()
            self._http = self._build_http_client()

    def sl_call(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        """Execute an authenticated Service Layer call.

        Args:
            method: HTTP verb (GET, POST, PATCH, PUT, DELETE).
            path:   Path relative to SL_BASE_URL, e.g. ``ProductionOrders(42)``.
            body:   JSON body for write requests.
            params: OData query parameters, e.g. ``{"$filter": "...", "$top": "10"}``.

        Returns:
            Parsed JSON response body (dict / list).  None for 204 No Content.

        Raises:
            ServiceLayerError: HTTP ≥ 400 from SAP.
            DryRunError:        Write attempted with DRY_RUN=true.
        """
        method = method.upper()

        if method in _WRITE_METHODS and self._cfg.dry_run:
            logger.warning("service_layer.dry_run_blocked", method=method, path=path)
            raise DryRunError(f"DRY_RUN active – {method} {path} not sent to SAP")

        with self._lock:
            self._ensure_session()
            try:
                return self._request(method, path, body=body, params=params)
            except ServiceLayerError as exc:
                if exc.status == 401:
                    logger.warning("service_layer.401_relogin", path=path)
                    self._clear_session()
                    self._ensure_session()
                    return self._request(method, path, body=body, params=params)
                raise

    def logout(self) -> None:
        """Explicitly log out and discard the session."""
        with self._lock:
            if self._cookies:
                try:
                    self._http.post(
                        f"{self._cfg.base_url}/Logout",
                        headers=self._cookie_header(),
                        timeout=5.0,
                    )
                except Exception:
                    pass
            self._clear_session()
        logger.info("service_layer.logout")

    def probe(self) -> bool:
        """Return True if the Service Layer is reachable and login succeeds."""
        try:
            with self._lock:
                self._ensure_session()
            return True
        except Exception as exc:
            logger.warning("service_layer.probe.failed", error=str(exc))
            return False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_http_client(self) -> httpx.Client:
        verify = not self._cfg.allow_invalid_cert
        return httpx.Client(
            verify=verify,
            timeout=self._cfg.timeout_seconds,
            headers={"Accept": "application/json"},
            follow_redirects=True,
        )

    def _session_valid(self) -> bool:
        return (
            bool(self._cookies)
            and self._company_db == self.company_db
            and time.monotonic() < self._session_expires_at - _SESSION_REFRESH_BUFFER
        )

    def _ensure_session(self) -> None:
        """Login if no valid session exists, then fetch CSRF token."""
        if self._session_valid():
            return
        self._login()
        self._fetch_csrf()

    def _login(self) -> None:
        url = f"{self._cfg.base_url}/Login"
        payload = {
            "CompanyDB": self.company_db,
            "UserName": self._cfg.username,
            "Password": self._cfg.password,
        }
        logger.info("service_layer.login", company_db=self.company_db, url=url)
        try:
            resp = self._http.post(url, json=payload)
        except httpx.RequestError as exc:
            raise ServiceLayerError(0, f"Login network error: {exc}") from exc

        if resp.status_code >= 400:
            msg = _extract_error(resp)
            raise ServiceLayerError(resp.status_code, f"Login failed: {msg}")

        self._cookies = _extract_cookies(resp)
        self._company_db = self.company_db
        self._session_expires_at = time.monotonic() + _SESSION_TTL_SECONDS
        self._csrf_token = ""
        logger.info("service_layer.login.ok", company_db=self._company_db)

    def _fetch_csrf(self) -> None:
        """GET $top=0 on a lightweight entity to retrieve the CSRF token."""
        url = f"{self._cfg.base_url}/CompanyService_GetCompanyInfo"
        try:
            resp = self._http.get(
                url,
                headers={**self._cookie_header(), "X-CSRF-Token": "Fetch"},
            )
            token = resp.headers.get("X-CSRF-Token", "")
            self._merge_cookies(resp)
            if token and token.lower() != "fetch":
                self._csrf_token = token
                logger.debug("service_layer.csrf.fetched")
            else:
                logger.debug("service_layer.csrf.not_returned")
        except Exception as exc:
            logger.warning("service_layer.csrf.fetch_failed", error=str(exc))

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        url = f"{self._cfg.base_url}/{path}"
        headers = {**self._cookie_header()}

        if method in _WRITE_METHODS:
            headers["Content-Type"] = "application/json"
            if self._csrf_token:
                headers["X-CSRF-Token"] = self._csrf_token

        try:
            resp = self._http.request(
                method,
                url,
                json=body,
                params=params,
                headers=headers,
            )
        except httpx.RequestError as exc:
            raise ServiceLayerError(0, f"Network error: {exc}") from exc

        self._merge_cookies(resp)

        if resp.status_code == 204:
            return None

        if resp.status_code >= 400:
            msg = _extract_error(resp)
            logger.warning(
                "service_layer.error",
                status=resp.status_code,
                method=method,
                path=path,
                message=msg,
            )
            raise ServiceLayerError(resp.status_code, msg)

        logger.debug("service_layer.ok", method=method, path=path, status=resp.status_code)
        return resp.json()

    def _cookie_header(self) -> dict[str, str]:
        if not self._cookies:
            return {}
        cookie_str = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
        return {"Cookie": cookie_str}

    def _merge_cookies(self, resp: httpx.Response) -> None:
        for k, v in resp.cookies.items():
            self._cookies[k] = v

    def _clear_session(self) -> None:
        self._cookies = {}
        self._csrf_token = ""
        self._session_expires_at = 0.0
        self._company_db = ""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _extract_cookies(resp: httpx.Response) -> dict[str, str]:
    """Extract B1SESSION and ROUTEID from response cookies."""
    result = {}
    for name in ("B1SESSION", "ROUTEID"):
        v = resp.cookies.get(name, "")
        if v:
            result[name] = v
    # Fallback: parse Set-Cookie header manually
    if not result:
        for header_val in resp.headers.get_list("Set-Cookie"):
            for part in header_val.split(";"):
                part = part.strip()
                if "=" in part:
                    k, v = part.split("=", 1)
                    if k.strip() in ("B1SESSION", "ROUTEID"):
                        result[k.strip()] = v.strip()
    return result


def _extract_error(resp: httpx.Response) -> str:
    """Extract the OData error message from the response body."""
    try:
        data = resp.json()
        return (
            data.get("error", {}).get("message", {}).get("value")
            or data.get("error", {}).get("message")
            or resp.text[:200]
        )
    except Exception:
        return resp.text[:200]
