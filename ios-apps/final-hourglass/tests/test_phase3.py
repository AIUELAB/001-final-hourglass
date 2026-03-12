"""Comprehensive unit tests for iOS Release CLI Phase 3 modules.

Covers:
- cli.utils.asc_api (ASCApiClient, ASCApiError)
- cli.steps.metadata (run_metadata)
- cli.steps.submit (run_submit)
"""

# pyright: reportPrivateUsage=false, reportOperatorIssue=false
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.config import ReleaseConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# A minimal EC private key in PEM format (P-384 / secp384r1).
# This is a throwaway test-only key - NOT a real secret.
MOCK_P8_KEY = """\
-----BEGIN EC PRIVATE KEY-----
MHQCAQEEIBkg4LVWM9buwBsxAkOL6MFHV1MkzCZ0wKqmLEUN0JzoAcGBSuBBAAi
oWQDYgAE2a2gLqdjJxp4dD3VRyFaFnYBKBDqHQdrPelAs+gI+bSuEVBFMqbfPKSC
cJIXKn6qRU7t5JAy1VkMGKwT3bKCERxmHxZC8BjTUvJnVEHKmyWQz3EKkBmZiR1j
vReJ2RPs
-----END EC PRIVATE KEY-----
"""


@pytest.fixture()
def p8_file(tmp_path: Path) -> Path:
    """Create a temporary .p8 key file."""
    key_file = tmp_path / "AuthKey_TEST.p8"
    key_file.write_text(MOCK_P8_KEY)
    return key_file


def make_config(tmp_path: Path, *, p8_exists: bool = True) -> ReleaseConfig:
    """Build a ReleaseConfig with test values.

    Args:
        tmp_path: pytest tmp_path fixture.
        p8_exists: If True, create a real .p8 file on disk.
    """
    from cli.config import ReleaseConfig

    if p8_exists:
        key_file = tmp_path / "AuthKey_TEST.p8"
        key_file.write_text(MOCK_P8_KEY)
        key_path = str(key_file)
    else:
        key_path = str(tmp_path / "missing.p8")

    return ReleaseConfig(
        api_key_id="TESTKEY123",
        api_issuer_id="test-issuer-uuid",
        api_key_path=key_path,
        team_id="N4UHXSGNLU",
        bundle_id="com.AIUELAB.FinalHourglass",
        project_root=tmp_path,
    )


def make_config_no_credentials(tmp_path: Path) -> ReleaseConfig:
    """Build a ReleaseConfig with missing credentials."""
    from cli.config import ReleaseConfig

    return ReleaseConfig(
        api_key_id="",
        api_issuer_id="",
        api_key_path="",
        team_id="N4UHXSGNLU",
        bundle_id="com.AIUELAB.FinalHourglass",
        project_root=tmp_path,
    )


# ---------------------------------------------------------------------------
# Mock data helpers
# ---------------------------------------------------------------------------


def _mock_app(app_id: str = "APP123", name: str = "FinalHourglass") -> dict:
    return {
        "id": app_id,
        "type": "apps",
        "attributes": {"name": name, "bundleId": "com.AIUELAB.FinalHourglass"},
    }


def _mock_version(
    version_id: str = "VER456",
    version_string: str = "1.0.11",
    state: str = "PREPARE_FOR_SUBMISSION",
) -> dict:
    return {
        "id": version_id,
        "type": "appStoreVersions",
        "attributes": {
            "versionString": version_string,
            "appVersionState": state,
            "appStoreState": state,
        },
    }


def _mock_localization(
    loc_id: str = "LOC789",
    locale: str = "ja-JP",
    whats_new: str = "Bug fixes",
) -> dict:
    return {
        "id": loc_id,
        "type": "appStoreVersionLocalizations",
        "attributes": {"locale": locale, "whatsNew": whats_new},
    }


def _mock_build(build_version: str = "42") -> dict:
    return {
        "id": "BUILD999",
        "type": "builds",
        "attributes": {"version": build_version},
    }


# ============================================================================
# Tests for cli.utils.asc_api
# ============================================================================


class TestASCApiClient:
    """Tests for ASCApiClient."""

    # -- JWT generation --------------------------------------------------

    @patch("cli.utils.asc_api.jwt.encode", return_value="mock.jwt.token")
    def test_generate_jwt_header_and_payload(self, mock_encode, p8_file):
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID123", "ISS456", p8_file)
        token = client._generate_jwt()

        assert token == "mock.jwt.token"
        mock_encode.assert_called_once()

        call_args = mock_encode.call_args
        payload = call_args[0][0]
        headers = call_args[1]["headers"]

        # Header checks
        assert headers["kid"] == "KID123"
        assert headers["typ"] == "JWT"

        # Payload checks
        assert payload["iss"] == "ISS456"
        assert payload["aud"] == "appstoreconnect-v1"
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] - payload["iat"] == 20 * 60

    # -- _request: success -----------------------------------------------

    def test_request_success_200(self, p8_file):
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID", "ISS", p8_file)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {"data": []}

        with patch.object(client._session, "request", return_value=mock_response):
            with patch.object(client, "_get_token", return_value="tok"):
                result = client._request("GET", "/apps")

        assert result == {"data": []}

    def test_request_success_204_empty_body(self, p8_file):
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID", "ISS", p8_file)

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.ok = True

        with patch.object(client._session, "request", return_value=mock_response):
            with patch.object(client, "_get_token", return_value="tok"):
                result = client._request("PATCH", "/something")

        assert result == {}

    # -- _request: 429 retry with Retry-After ----------------------------

    @patch("cli.utils.asc_api.time.sleep")
    def test_request_429_retry_then_success(self, mock_sleep, p8_file):
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID", "ISS", p8_file)

        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.ok = False
        resp_429.headers = {"Retry-After": "2"}

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.ok = True
        resp_200.json.return_value = {"data": "ok"}

        with patch.object(client._session, "request", side_effect=[resp_429, resp_200]):
            with patch.object(client, "_get_token", return_value="tok"):
                result = client._request("GET", "/apps")

        assert result == {"data": "ok"}
        mock_sleep.assert_called_once_with(2)

    @patch("cli.utils.asc_api.time.sleep")
    def test_request_429_exhausts_retries(self, _mock_sleep, p8_file):
        from cli.utils.asc_api import ASCApiClient, ASCApiError

        client = ASCApiClient("KID", "ISS", p8_file)

        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.ok = False
        resp_429.headers = {"Retry-After": "1"}
        resp_429.json.return_value = {"errors": [{"detail": "Rate limit"}]}
        resp_429.text = "Rate limit"

        with patch.object(client._session, "request", return_value=resp_429):
            with patch.object(client, "_get_token", return_value="tok"):
                with pytest.raises(ASCApiError) as exc_info:
                    client._request("GET", "/apps")

        assert exc_info.value.status_code == 429

    # -- _request: 401 JWT re-generation retry ---------------------------

    def test_request_401_regenerate_jwt_then_success(self, p8_file):
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID", "ISS", p8_file)

        resp_401 = MagicMock()
        resp_401.status_code = 401
        resp_401.ok = False

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.ok = True
        resp_200.json.return_value = {"data": "refreshed"}

        with patch.object(client._session, "request", side_effect=[resp_401, resp_200]):
            with patch.object(client, "_get_token", return_value="tok"):
                result = client._request("GET", "/apps")

        assert result == {"data": "refreshed"}
        # JWT token was cleared and then regenerated via _get_token

    # -- _request: 4xx error raises ASCApiError --------------------------

    def test_request_4xx_raises_asc_api_error(self, p8_file):
        from cli.utils.asc_api import ASCApiClient, ASCApiError

        client = ASCApiClient("KID", "ISS", p8_file)

        resp_403 = MagicMock()
        resp_403.status_code = 403
        resp_403.ok = False
        resp_403.json.return_value = {"errors": [{"detail": "Forbidden access", "title": "FORBIDDEN"}]}
        resp_403.text = "Forbidden"

        with patch.object(client._session, "request", return_value=resp_403):
            with patch.object(client, "_get_token", return_value="tok"):
                with pytest.raises(ASCApiError) as exc_info:
                    client._request("GET", "/apps")

        assert exc_info.value.status_code == 403
        assert "Forbidden access" in exc_info.value.error_messages

    def test_request_4xx_error_without_json_body(self, p8_file):
        from cli.utils.asc_api import ASCApiClient, ASCApiError

        client = ASCApiClient("KID", "ISS", p8_file)

        resp_400 = MagicMock()
        resp_400.status_code = 400
        resp_400.ok = False
        resp_400.json.side_effect = ValueError("No JSON")
        resp_400.text = "Bad Request body"

        with patch.object(client._session, "request", return_value=resp_400):
            with patch.object(client, "_get_token", return_value="tok"):
                with pytest.raises(ASCApiError) as exc_info:
                    client._request("GET", "/apps")

        assert exc_info.value.status_code == 400
        assert "Bad Request body" in exc_info.value.error_messages[0]

    # -- find_app --------------------------------------------------------

    def test_find_app_returns_app(self, p8_file):
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID", "ISS", p8_file)

        with patch.object(client, "_request", return_value={"data": [_mock_app()]}):
            result = client.find_app("com.AIUELAB.FinalHourglass")

        assert result is not None
        assert result["id"] == "APP123"

    def test_find_app_returns_none_when_empty(self, p8_file):
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID", "ISS", p8_file)

        with patch.object(client, "_request", return_value={"data": []}):
            result = client.find_app("com.nonexistent")

        assert result is None

    # -- get_editable_version -------------------------------------------

    def test_get_editable_version_returns_prepare_for_submission(self, p8_file):
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID", "ISS", p8_file)

        versions = [
            _mock_version("V1", state="READY_FOR_SALE"),
            _mock_version("V2", state="PREPARE_FOR_SUBMISSION"),
        ]
        with patch.object(client, "_request", return_value={"data": versions}):
            result = client.get_editable_version("APP123")

        assert result is not None
        assert result["id"] == "V2"

    def test_get_editable_version_returns_none(self, p8_file):
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID", "ISS", p8_file)

        versions = [_mock_version("V1", state="READY_FOR_SALE")]
        with patch.object(client, "_request", return_value={"data": versions}):
            result = client.get_editable_version("APP123")

        assert result is None

    # -- get_version_localizations --------------------------------------

    def test_get_version_localizations(self, p8_file):
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID", "ISS", p8_file)

        locs = [_mock_localization("L1", "ja-JP"), _mock_localization("L2", "en-US")]
        with patch.object(client, "_request", return_value={"data": locs}):
            result = client.get_version_localizations("VER456")

        assert len(result) == 2
        assert result[0]["id"] == "L1"

    # -- update_whats_new -----------------------------------------------

    def test_update_whats_new_sends_correct_payload(self, p8_file):
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID", "ISS", p8_file)

        with patch.object(client, "_request", return_value={"data": {}}) as mock_req:
            client.update_whats_new("LOC789", "New release notes")

        mock_req.assert_called_once()
        call_args = mock_req.call_args
        assert call_args[0][0] == "PATCH"
        assert "/appStoreVersionLocalizations/LOC789" in call_args[0][1]

        payload = call_args[1]["json"]
        assert payload["data"]["type"] == "appStoreVersionLocalizations"
        assert payload["data"]["id"] == "LOC789"
        assert payload["data"]["attributes"]["whatsNew"] == "New release notes"

    # -- get_version_build ----------------------------------------------

    def test_get_version_build_returns_build(self, p8_file):
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID", "ISS", p8_file)

        with patch.object(client, "_request", return_value={"data": _mock_build()}):
            result = client.get_version_build("VER456")

        assert result is not None
        assert result["attributes"]["version"] == "42"

    def test_get_version_build_returns_none_on_404(self, p8_file):
        from cli.utils.asc_api import ASCApiClient, ASCApiError

        client = ASCApiClient("KID", "ISS", p8_file)

        with patch.object(client, "_request", side_effect=ASCApiError(404, ["Not Found"])):
            result = client.get_version_build("VER456")

        assert result is None

    def test_get_version_build_reraises_non_404(self, p8_file):
        from cli.utils.asc_api import ASCApiClient, ASCApiError

        client = ASCApiClient("KID", "ISS", p8_file)

        with patch.object(client, "_request", side_effect=ASCApiError(500, ["Server Error"])):
            with pytest.raises(ASCApiError) as exc_info:
                client.get_version_build("VER456")
            assert exc_info.value.status_code == 500

    # -- submit_for_review ----------------------------------------------

    def test_submit_for_review_sends_correct_payload(self, p8_file):
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID", "ISS", p8_file)

        with patch.object(client, "_request", return_value={"data": {}}) as mock_req:
            client.submit_for_review("VER456")

        mock_req.assert_called_once()
        call_args = mock_req.call_args
        assert call_args[0][0] == "POST"
        assert "/appStoreVersionSubmissions" in call_args[0][1]

        payload = call_args[1]["json"]
        assert payload["data"]["type"] == "appStoreVersionSubmissions"
        rel = payload["data"]["relationships"]["appStoreVersion"]["data"]
        assert rel["type"] == "appStoreVersions"
        assert rel["id"] == "VER456"

    # -- test_connection ------------------------------------------------

    def test_test_connection_success(self, p8_file):
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID", "ISS", p8_file)

        with patch.object(client, "_request", return_value={"data": []}):
            assert client.test_connection() is True

    def test_test_connection_asc_error(self, p8_file):
        from cli.utils.asc_api import ASCApiClient, ASCApiError

        client = ASCApiClient("KID", "ISS", p8_file)

        with patch.object(client, "_request", side_effect=ASCApiError(401, ["Unauthorized"])):
            assert client.test_connection() is False

    def test_test_connection_request_exception(self, p8_file):
        import requests
        from cli.utils.asc_api import ASCApiClient

        client = ASCApiClient("KID", "ISS", p8_file)

        with patch.object(client, "_request", side_effect=requests.ConnectionError("timeout")):
            assert client.test_connection() is False


# ============================================================================
# Tests for cli.steps.metadata
# ============================================================================


class TestRunMetadata:
    """Tests for run_metadata."""

    # -- dry_run: credential check fails ---------------------------------

    def test_dry_run_credential_check_fails(self, tmp_path):
        from cli.steps.metadata import run_metadata

        config = make_config_no_credentials(tmp_path)
        result = run_metadata(config, dry_run=True)

        assert result["success"] is False
        assert "Credential validation failed" in result["error"]
        assert result["dry_run"] is True

    # -- dry_run: normal flow --------------------------------------------

    def test_dry_run_normal_flow(self, tmp_path):
        from cli.steps.metadata import run_metadata

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_client.find_app.return_value = _mock_app()
        mock_client.get_editable_version.return_value = _mock_version()
        mock_client.get_version_localizations.return_value = [_mock_localization()]

        with patch("cli.steps.metadata.ASCApiClient", return_value=mock_client):
            result = run_metadata(config, dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["app_name"] == "FinalHourglass"
        assert result["version_string"] == "1.0.11"
        assert result["current_whats_new"] == "Bug fixes"
        assert result["locale"] == "ja-JP"

    # -- dry_run: app not found ------------------------------------------

    def test_dry_run_app_not_found(self, tmp_path):
        from cli.steps.metadata import run_metadata

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_client.find_app.return_value = None

        with patch("cli.steps.metadata.ASCApiClient", return_value=mock_client):
            result = run_metadata(config, dry_run=True)

        assert result["success"] is False
        assert "App not found" in result["error"]

    # -- dry_run: no editable version ------------------------------------

    def test_dry_run_no_editable_version(self, tmp_path):
        from cli.steps.metadata import run_metadata

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_client.find_app.return_value = _mock_app()
        mock_client.get_editable_version.return_value = None

        with patch("cli.steps.metadata.ASCApiClient", return_value=mock_client):
            result = run_metadata(config, dry_run=True)

        assert result["success"] is True
        assert "warning" in result
        assert "PREPARE_FOR_SUBMISSION" in result["warning"]

    # -- execute: whats_new empty returns error --------------------------

    def test_execute_whats_new_empty(self, tmp_path):
        from cli.steps.metadata import run_metadata

        config = make_config(tmp_path)

        mock_client = MagicMock()

        with patch("cli.steps.metadata.ASCApiClient", return_value=mock_client):
            result = run_metadata(config, whats_new="", dry_run=False)

        assert result["success"] is False
        assert "whats_new is required" in result["error"]

    # -- execute: normal flow updates whats_new --------------------------

    def test_execute_normal_flow(self, tmp_path):
        from cli.steps.metadata import run_metadata

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_client.find_app.return_value = _mock_app()
        mock_client.get_editable_version.return_value = _mock_version()
        mock_client.get_version_localizations.return_value = [_mock_localization(whats_new="Old notes")]
        mock_client.update_whats_new.return_value = {}

        with patch("cli.steps.metadata.ASCApiClient", return_value=mock_client):
            result = run_metadata(
                config,
                whats_new="New release notes v1.0.11",
                dry_run=False,
            )

        assert result["success"] is True
        assert result["dry_run"] is False
        assert result["new_whats_new"] == "New release notes v1.0.11"
        assert result["old_whats_new"] == "Old notes"
        assert result["locale"] == "ja-JP"
        mock_client.update_whats_new.assert_called_once_with("LOC789", "New release notes v1.0.11")

    # -- execute: ASCApiError handled ------------------------------------

    def test_execute_asc_api_error_handled(self, tmp_path):
        from cli.steps.metadata import run_metadata
        from cli.utils.asc_api import ASCApiError

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_client.find_app.side_effect = ASCApiError(500, ["Server Error"])

        with patch("cli.steps.metadata.ASCApiClient", return_value=mock_client):
            result = run_metadata(config, whats_new="notes", dry_run=False)

        assert result["success"] is False
        assert "ASC API error" in result["error"]

    # -- dry_run: auth failure returns error -----------------------------

    def test_dry_run_auth_failure(self, tmp_path):
        from cli.steps.metadata import run_metadata

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = False

        with patch("cli.steps.metadata.ASCApiClient", return_value=mock_client):
            result = run_metadata(config, dry_run=True)

        assert result["success"] is False
        assert "authentication failed" in result["error"]
        assert result["dry_run"] is True

    # -- execute: auth failure returns error ----------------------------

    def test_execute_auth_failure(self, tmp_path):
        from cli.steps.metadata import run_metadata

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = False

        with patch("cli.steps.metadata.ASCApiClient", return_value=mock_client):
            result = run_metadata(config, whats_new="notes", dry_run=False)

        assert result["success"] is False
        assert "authentication failed" in result["error"]

    # -- execute: en-US fallback when ja-JP missing --------------------

    def test_execute_en_us_fallback(self, tmp_path):
        from cli.steps.metadata import run_metadata

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_client.find_app.return_value = _mock_app()
        mock_client.get_editable_version.return_value = _mock_version()
        mock_client.get_version_localizations.return_value = [
            _mock_localization(loc_id="LOC_EN", locale="en-US", whats_new="Old EN")
        ]
        mock_client.update_whats_new.return_value = {}

        with patch("cli.steps.metadata.ASCApiClient", return_value=mock_client):
            result = run_metadata(config, whats_new="New notes", dry_run=False)

        assert result["success"] is True
        assert result["locale"] == "en-US"
        mock_client.update_whats_new.assert_called_once_with("LOC_EN", "New notes")

    # -- dry_run: ASCApiError handled ------------------------------------

    def test_dry_run_asc_api_error_handled(self, tmp_path):
        from cli.steps.metadata import run_metadata
        from cli.utils.asc_api import ASCApiError

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.side_effect = ASCApiError(403, ["Forbidden"])

        with patch("cli.steps.metadata.ASCApiClient", return_value=mock_client):
            result = run_metadata(config, dry_run=True)

        assert result["success"] is False
        assert result["dry_run"] is True


# ============================================================================
# Tests for cli.steps.submit
# ============================================================================


class TestRunSubmit:
    """Tests for run_submit."""

    # -- dry_run: credential check fails ---------------------------------

    def test_dry_run_credential_check_fails(self, tmp_path):
        from cli.steps.submit import run_submit

        config = make_config_no_credentials(tmp_path)
        result = run_submit(config, dry_run=True)

        assert result["success"] is False
        assert "Credential validation failed" in result["error"]
        assert result["dry_run"] is True

    # -- dry_run: normal flow shows ready status -------------------------

    def test_dry_run_normal_flow_ready(self, tmp_path):
        from cli.steps.submit import run_submit

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_client.find_app.return_value = _mock_app()
        mock_client.get_editable_version.return_value = _mock_version()
        mock_client.get_version_build.return_value = _mock_build("55")

        with patch("cli.steps.submit.ASCApiClient", return_value=mock_client):
            result = run_submit(config, dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["version"] == "1.0.11"
        assert result["build_version"] == "55"

    # -- dry_run: no editable version returns success+warning ------------

    def test_dry_run_no_editable_version(self, tmp_path):
        from cli.steps.submit import run_submit

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_client.find_app.return_value = _mock_app()
        mock_client.get_editable_version.return_value = None

        with patch("cli.steps.submit.ASCApiClient", return_value=mock_client):
            result = run_submit(config, dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        assert "warning" in result
        assert "PREPARE_FOR_SUBMISSION" in result["warning"]

    # -- dry_run: no build returns success+warning -----------------------

    def test_dry_run_no_build(self, tmp_path):
        from cli.steps.submit import run_submit

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_client.find_app.return_value = _mock_app()
        mock_client.get_editable_version.return_value = _mock_version()
        mock_client.get_version_build.return_value = None

        with patch("cli.steps.submit.ASCApiClient", return_value=mock_client):
            result = run_submit(config, dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        assert "warning" in result
        assert "No build attached" in result["warning"]

    # -- execute: no editable version returns error ----------------------

    def test_execute_no_editable_version(self, tmp_path):
        from cli.steps.submit import run_submit

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_client.find_app.return_value = _mock_app()
        mock_client.get_editable_version.return_value = None

        with patch("cli.steps.submit.ASCApiClient", return_value=mock_client):
            result = run_submit(config, dry_run=False)

        assert result["success"] is False
        assert result["dry_run"] is False
        assert "No version" in result["error"]

    # -- execute: no build returns error ---------------------------------

    def test_execute_no_build(self, tmp_path):
        from cli.steps.submit import run_submit

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_client.find_app.return_value = _mock_app()
        mock_client.get_editable_version.return_value = _mock_version()
        mock_client.get_version_build.return_value = None

        with patch("cli.steps.submit.ASCApiClient", return_value=mock_client):
            result = run_submit(config, dry_run=False)

        assert result["success"] is False
        assert result["dry_run"] is False
        assert "No build attached" in result["error"]

    # -- execute: normal submission --------------------------------------

    def test_execute_normal_submission(self, tmp_path):
        from cli.steps.submit import run_submit

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_client.find_app.return_value = _mock_app()
        mock_client.get_editable_version.return_value = _mock_version()
        mock_client.get_version_build.return_value = _mock_build("77")
        mock_client.submit_for_review.return_value = {"data": {}}

        with patch("cli.steps.submit.ASCApiClient", return_value=mock_client):
            result = run_submit(config, dry_run=False)

        assert result["success"] is True
        assert result["dry_run"] is False
        assert result["version"] == "1.0.11"
        assert result["build_version"] == "77"
        mock_client.submit_for_review.assert_called_once_with("VER456")

    # -- execute: ASCApiError handled ------------------------------------

    def test_execute_asc_api_error(self, tmp_path):
        from cli.steps.submit import run_submit
        from cli.utils.asc_api import ASCApiError

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_client.find_app.side_effect = ASCApiError(500, ["Internal"])

        with patch("cli.steps.submit.ASCApiClient", return_value=mock_client):
            result = run_submit(config, dry_run=False)

        assert result["success"] is False
        assert "App Store Connect API error" in result["error"]

    # -- execute: auth failure -------------------------------------------

    def test_execute_auth_failure(self, tmp_path):
        from cli.steps.submit import run_submit

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = False

        with patch("cli.steps.submit.ASCApiClient", return_value=mock_client):
            result = run_submit(config, dry_run=False)

        assert result["success"] is False
        assert "authentication failed" in result["error"]

    # -- app not found ---------------------------------------------------

    def test_execute_app_not_found(self, tmp_path):
        from cli.steps.submit import run_submit

        config = make_config(tmp_path)

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_client.find_app.return_value = None

        with patch("cli.steps.submit.ASCApiClient", return_value=mock_client):
            result = run_submit(config, dry_run=False)

        assert result["success"] is False
        assert "App not found" in result["error"]
