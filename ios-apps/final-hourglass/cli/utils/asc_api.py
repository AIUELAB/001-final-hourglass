"""App Store Connect API v1 client with JWT Bearer Token authentication."""

from __future__ import annotations

import time
from pathlib import Path

import jwt
import requests
from rich.console import Console

console = Console()

BASE_URL = "https://api.appstoreconnect.apple.com/v1"
JWT_AUDIENCE = "appstoreconnect-v1"
JWT_ALGORITHM = "ES256"
JWT_EXPIRY_SECONDS = 20 * 60  # 20 minutes
MAX_RETRIES = 3


class ASCApiError(Exception):
    """Error returned by the App Store Connect API."""

    def __init__(self, status_code: int, error_messages: list[str]) -> None:
        self.status_code = status_code
        self.error_messages = error_messages
        combined = "; ".join(error_messages) if error_messages else f"HTTP {status_code}"
        super().__init__(f"ASC API error {status_code}: {combined}")


class ASCApiClient:
    """Client for the App Store Connect API v1.

    Uses ES256 JWT Bearer Token authentication.

    Args:
        key_id: The Key ID from App Store Connect (e.g., "ABC123DEFG").
        issuer_id: The Issuer ID from App Store Connect.
        key_path: Path to the .p8 private key file.
    """

    def __init__(self, key_id: str, issuer_id: str, key_path: Path) -> None:
        self._key_id = key_id
        self._issuer_id = issuer_id
        self._key_path = key_path
        self._private_key = key_path.read_text()
        self._session = requests.Session()
        self._jwt_token: str | None = None
        self._jwt_expiry: float = 0.0

    def _generate_jwt(self) -> str:
        """Generate an ES256-signed JWT for App Store Connect API authentication.

        Returns:
            A signed JWT string valid for 20 minutes.
        """
        now = time.time()
        payload = {
            "iss": self._issuer_id,
            "iat": int(now),
            "exp": int(now + JWT_EXPIRY_SECONDS),
            "aud": JWT_AUDIENCE,
        }
        headers = {
            "kid": self._key_id,
            "typ": "JWT",
        }
        token: str = jwt.encode(
            payload,
            self._private_key,
            algorithm=JWT_ALGORITHM,
            headers=headers,
        )
        self._jwt_token = token
        self._jwt_expiry = now + JWT_EXPIRY_SECONDS
        return token

    def _get_token(self) -> str:
        """Return a valid JWT, generating a new one if expired."""
        if self._jwt_token is None or time.time() >= self._jwt_expiry - 30:
            return self._generate_jwt()
        return self._jwt_token

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Send an authenticated request to the App Store Connect API.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE).
            path: API path relative to v1 (e.g., "/apps").
            json: JSON body for POST/PATCH requests.
            params: Query parameters.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            ASCApiError: On 4xx/5xx responses (after retries for 429/401).

        Note:
            429 and 401 retries share the same MAX_RETRIES budget. In the
            unlikely event both occur in the same request cycle, the total
            retry count is still bounded by MAX_RETRIES.
        """
        url = f"{BASE_URL}{path}"
        auth_regenerated = False

        response: requests.Response | None = None

        for attempt in range(MAX_RETRIES + 1):
            token = self._get_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            response = self._session.request(
                method,
                url,
                headers=headers,
                json=json,
                params=params,
                timeout=(10, 30),
            )

            # 429 Too Many Requests — respect Retry-After
            if response.status_code == 429:
                if attempt >= MAX_RETRIES:
                    break
                raw_retry = response.headers.get("Retry-After", "5")
                try:
                    retry_after = int(raw_retry)
                except ValueError:
                    retry_after = 5  # Fallback for date-format Retry-After
                console.print(
                    f"[yellow]Rate limited. Retrying after {retry_after}s "
                    f"(attempt {attempt + 1}/{MAX_RETRIES})...[/yellow]"
                )
                time.sleep(retry_after)
                continue

            # 401 Unauthorized — regenerate JWT once and retry
            if response.status_code == 401 and not auth_regenerated:
                console.print("[yellow]401 received. Regenerating JWT...[/yellow]")
                self._jwt_token = None
                auth_regenerated = True
                continue

            # Success
            if response.ok:
                if response.status_code == 204:
                    return {}
                return response.json()

            # Other errors — break and raise
            break

        if response is None:
            raise ASCApiError(0, ["No response received"])

        # Parse error messages from response body
        error_messages = _parse_error_messages(response)
        raise ASCApiError(response.status_code, error_messages)

    def find_app(self, bundle_id: str) -> dict | None:
        """Find an app by its bundle ID.

        Args:
            bundle_id: The app's bundle identifier (e.g., "com.example.app").

        Returns:
            The app resource dict, or None if not found.
        """
        data = self._request("GET", "/apps", params={"filter[bundleId]": bundle_id})
        apps = data.get("data", [])
        return apps[0] if apps else None

    def get_editable_version(self, app_id: str) -> dict | None:
        """Get the editable (PREPARE_FOR_SUBMISSION) app store version.

        Args:
            app_id: The app's resource ID.

        Returns:
            The appStoreVersion resource dict, or None if no editable version exists.
        """
        data = self._request("GET", f"/apps/{app_id}/appStoreVersions")
        versions = data.get("data", [])
        for version in versions:
            state = version.get("attributes", {}).get("appVersionState", "")
            if state == "PREPARE_FOR_SUBMISSION":
                return version
        return None

    def find_version_by_string(self, app_id: str, version_string: str) -> dict | None:
        """Find an app store version by its version string (e.g. '1.0.13').

        Returns the version regardless of its state.

        Args:
            app_id: The app's resource ID.
            version_string: The version string to search for.

        Returns:
            The appStoreVersion resource dict, or None if not found.
        """
        data = self._request(
            "GET",
            f"/apps/{app_id}/appStoreVersions",
            params={"filter[versionString]": version_string},
        )
        versions = data.get("data", [])
        if versions:
            return versions[0]
        return None

    def get_version_localizations(self, version_id: str) -> list[dict]:
        """Get all localizations for an app store version.

        Args:
            version_id: The appStoreVersion resource ID.

        Returns:
            List of appStoreVersionLocalization resource dicts.
        """
        data = self._request("GET", f"/appStoreVersions/{version_id}/appStoreVersionLocalizations")
        return data.get("data", [])

    def update_whats_new(self, localization_id: str, whats_new: str) -> dict:
        """Update the "What's New" text for a localization.

        Args:
            localization_id: The appStoreVersionLocalization resource ID.
            whats_new: The new "What's New" text.

        Returns:
            The updated localization resource dict.
        """
        payload = {
            "data": {
                "type": "appStoreVersionLocalizations",
                "id": localization_id,
                "attributes": {
                    "whatsNew": whats_new,
                },
            }
        }
        return self._request("PATCH", f"/appStoreVersionLocalizations/{localization_id}", json=payload)

    def get_version_build(self, version_id: str) -> dict | None:
        """Get the build attached to an app store version.

        Args:
            version_id: The appStoreVersion resource ID.

        Returns:
            The build resource dict, or None if no build is attached.
        """
        try:
            data = self._request("GET", f"/appStoreVersions/{version_id}/build")
            return data.get("data")
        except ASCApiError as e:
            if e.status_code == 404:
                return None
            raise

    def create_version(self, app_id: str, version_string: str, platform: str = "IOS") -> dict:
        """Create a new App Store version.

        Args:
            app_id: The app's resource ID.
            version_string: The version string (e.g., "1.2.0").
            platform: The platform (default: "IOS").

        Returns:
            The created appStoreVersion resource dict.
        """
        payload = {
            "data": {
                "type": "appStoreVersions",
                "attributes": {
                    "platform": platform,
                    "versionString": version_string,
                },
                "relationships": {
                    "app": {
                        "data": {
                            "type": "apps",
                            "id": app_id,
                        }
                    }
                },
            }
        }
        return self._request("POST", "/appStoreVersions", json=payload)

    def attach_build(self, version_id: str, build_id: str) -> dict:
        """Attach a build to an app store version.

        Args:
            version_id: The appStoreVersion resource ID.
            build_id: The build resource ID to attach.

        Returns:
            The response dict.
        """
        payload = {
            "data": {
                "type": "builds",
                "id": build_id,
            }
        }
        return self._request(
            "PATCH",
            f"/appStoreVersions/{version_id}/relationships/build",
            json=payload,
        )

    def find_build(
        self,
        app_id: str,
        version_string: str,
    ) -> dict | None:
        """Find a processed build for an app by version string.

        Args:
            app_id: The app's resource ID.
            version_string: The version string to filter by.

        Returns:
            The build resource dict, or None if no matching build is found.
        """
        params = {
            "filter[app]": app_id,
            "filter[preReleaseVersion.version]": version_string,
            "filter[processingState]": "VALID",
            "sort": "-uploadedDate",
            "limit": "1",
        }
        data = self._request("GET", "/builds", params=params)
        builds = data.get("data", [])
        return builds[0] if builds else None

    def submit_for_review(self, version_id: str) -> dict:
        """Submit an app store version for review.

        Args:
            version_id: The appStoreVersion resource ID.

        Returns:
            The appStoreVersionSubmission resource dict.
        """
        payload = {
            "data": {
                "type": "appStoreVersionSubmissions",
                "relationships": {
                    "appStoreVersion": {
                        "data": {
                            "type": "appStoreVersions",
                            "id": version_id,
                        }
                    }
                },
            }
        }
        return self._request("POST", "/appStoreVersionSubmissions", json=payload)

    def test_connection(self) -> bool:
        """Test API authentication by making a lightweight request.

        Returns:
            True if authentication succeeds, False otherwise.
        """
        try:
            self._request("GET", "/apps", params={"limit": "1"})
            return True
        except ASCApiError:
            return False
        except requests.RequestException:
            return False


def _parse_error_messages(response: requests.Response) -> list[str]:
    """Extract error messages from an ASC API error response.

    Args:
        response: The HTTP response object.

    Returns:
        List of human-readable error message strings.
    """
    messages: list[str] = []
    try:
        body = response.json()
        for error in body.get("errors", []):
            detail = error.get("detail", "")
            title = error.get("title", "")
            if detail:
                messages.append(detail)
            elif title:
                messages.append(title)
    except (ValueError, KeyError):
        pass

    if not messages:
        messages.append(response.text[:500] if response.text else f"HTTP {response.status_code}")

    return messages
