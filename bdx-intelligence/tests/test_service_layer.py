"""Tests for the SAP Business One Service Layer client.

All HTTP calls are intercepted with respx – no real SAP connection is made.
"""

from __future__ import annotations

import os

import httpx
import pytest
import respx

os.environ.setdefault("SL_BASE_URL", "https://sap.test:50000/b1s/v2")
os.environ.setdefault("SL_USERNAME", "B1i")
os.environ.setdefault("SL_PASSWORD", "B1Admin")
os.environ.setdefault("SL_COMPANY_DB_DEV", "DEV_SBO_TEST")
os.environ.setdefault("SL_COMPANY_DB_PROD", "SBO_TEST")
os.environ.setdefault("SL_ALLOW_INVALID_CERT", "true")

from bdx.config import SapMode, ServiceLayerSettings
from bdx.sap_sl.client import DryRunError, ServiceLayerClient, ServiceLayerError


@pytest.fixture
def sl_settings() -> ServiceLayerSettings:
    return ServiceLayerSettings(
        base_url="https://sap.test:50000/b1s/v2",
        username="B1i",
        password="B1Admin",
        company_db_dev="DEV_SBO_TEST",
        company_db_prod="SBO_TEST",
        allow_invalid_cert=True,
        timeout_ms=5_000,
        dry_run=False,
    )


@pytest.fixture
def sl_settings_dry(sl_settings: ServiceLayerSettings) -> ServiceLayerSettings:
    return ServiceLayerSettings(**{**sl_settings.model_dump(), "dry_run": True})


def _login_response(session_id: str = "SES-001", route_id: str = "node1") -> httpx.Response:
    return httpx.Response(
        200,
        json={"SessionId": session_id},
        headers={
            "Set-Cookie": (f"B1SESSION={session_id}; Path=/; HttpOnly, ROUTEID={route_id}; Path=/")
        },
    )


_CSRF_URL = "https://sap.test:50000/b1s/v2/CompanyService_GetCompanyInfo"


def _csrf_response(token: str = "CSRF-TOKEN-123") -> httpx.Response:
    return httpx.Response(200, json={}, headers={"X-CSRF-Token": token})


class TestLogin:
    @respx.mock
    def test_successful_login(self, sl_settings):
        respx.post("https://sap.test:50000/b1s/v2/Login").mock(return_value=_login_response())
        respx.get(_CSRF_URL).mock(return_value=_csrf_response())
        respx.get("https://sap.test:50000/b1s/v2/ProductionOrders").mock(
            return_value=httpx.Response(200, json={"value": []})
        )

        client = ServiceLayerClient(sl_settings, mode=SapMode.DEV)
        result = client.sl_call("GET", "ProductionOrders")
        assert result == {"value": []}

    @respx.mock
    def test_login_failure_raises(self, sl_settings):
        respx.post("https://sap.test:50000/b1s/v2/Login").mock(
            return_value=httpx.Response(
                401,
                json={"error": {"message": {"value": "Invalid credentials"}}},
            )
        )
        client = ServiceLayerClient(sl_settings, mode=SapMode.DEV)
        with pytest.raises(ServiceLayerError) as exc_info:
            client.sl_call("GET", "ProductionOrders")
        assert exc_info.value.status == 401
        assert "Invalid credentials" in exc_info.value.message


class TestCSRF:
    @respx.mock
    def test_csrf_token_sent_on_write(self, sl_settings):
        respx.post("https://sap.test:50000/b1s/v2/Login").mock(return_value=_login_response())
        respx.get(_CSRF_URL).mock(return_value=_csrf_response("MY-TOKEN"))

        patch_route = respx.patch("https://sap.test:50000/b1s/v2/ProductionOrders(42)").mock(
            return_value=httpx.Response(204)
        )

        client = ServiceLayerClient(sl_settings, mode=SapMode.DEV)
        client.sl_call("PATCH", "ProductionOrders(42)", body={"Status": "R"})

        assert patch_route.called
        sent_headers = patch_route.calls[0].request.headers
        assert sent_headers.get("x-csrf-token") == "MY-TOKEN"


class TestAutoRetry:
    @respx.mock
    def test_401_triggers_relogin(self, sl_settings):
        login_calls = []

        def login_side_effect(request):
            login_calls.append(request)
            return _login_response(f"SES-{len(login_calls)}")

        respx.post("https://sap.test:50000/b1s/v2/Login").mock(side_effect=login_side_effect)
        respx.get(_CSRF_URL).mock(return_value=_csrf_response())

        get_route = respx.get("https://sap.test:50000/b1s/v2/BusinessPartners")
        get_route.side_effect = [
            httpx.Response(401, json={"error": {"message": {"value": "Session expired"}}}),
            httpx.Response(200, json={"value": [{"CardCode": "C001"}]}),
        ]

        client = ServiceLayerClient(sl_settings, mode=SapMode.DEV)
        result = client.sl_call("GET", "BusinessPartners")
        assert result == {"value": [{"CardCode": "C001"}]}
        assert len(login_calls) == 2  # initial login + relogin after 401


class TestDryRun:
    @respx.mock
    def test_write_blocked_in_dry_run(self, sl_settings_dry):
        respx.post("https://sap.test:50000/b1s/v2/Login").mock(return_value=_login_response())
        respx.get(_CSRF_URL).mock(return_value=_csrf_response())

        client = ServiceLayerClient(sl_settings_dry, mode=SapMode.DEV)
        with pytest.raises(DryRunError):
            client.sl_call("POST", "ProductionOrders", body={"DocEntry": 1})

    @respx.mock
    def test_get_allowed_in_dry_run(self, sl_settings_dry):
        respx.post("https://sap.test:50000/b1s/v2/Login").mock(return_value=_login_response())
        respx.get(_CSRF_URL).mock(return_value=_csrf_response())
        respx.get("https://sap.test:50000/b1s/v2/ProductionOrders").mock(
            return_value=httpx.Response(200, json={"value": []})
        )

        client = ServiceLayerClient(sl_settings_dry, mode=SapMode.DEV)
        result = client.sl_call("GET", "ProductionOrders")
        assert result == {"value": []}


class TestModeSwitch:
    @respx.mock
    def test_switch_mode_clears_session(self, sl_settings):
        respx.post("https://sap.test:50000/b1s/v2/Login").mock(return_value=_login_response())
        respx.get(_CSRF_URL).mock(return_value=_csrf_response())
        respx.get("https://sap.test:50000/b1s/v2/ProductionOrders").mock(
            return_value=httpx.Response(200, json={"value": []})
        )

        client = ServiceLayerClient(sl_settings, mode=SapMode.DEV)
        client.sl_call("GET", "ProductionOrders")
        assert client.company_db == "DEV_SBO_TEST"

        client.switch_mode(SapMode.PROD)
        assert client.mode == SapMode.PROD
        assert client.company_db == "SBO_TEST"
        # Session must have been cleared
        assert client._cookies == {}


class TestSettings:
    def test_company_db_for_dev(self, sl_settings):
        assert sl_settings.company_db_for_mode(SapMode.DEV) == "DEV_SBO_TEST"

    def test_company_db_for_prod(self, sl_settings):
        assert sl_settings.company_db_for_mode(SapMode.PROD) == "SBO_TEST"

    def test_configured_true_when_url_and_user_set(self, sl_settings):
        assert sl_settings.configured is True

    def test_configured_false_when_no_url(self):
        s = ServiceLayerSettings(
            base_url="",
            username="B1i",
            password="x",
            company_db_dev="DEV",
            company_db_prod="PROD",
        )
        assert s.configured is False

    def test_write_enabled_false_in_dry_run(self, sl_settings_dry):
        assert sl_settings_dry.write_enabled is False
