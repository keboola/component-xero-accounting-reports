from typing import Any

import requests
from keboola.component.exceptions import UserException


class XeroClient:
    BASE_URL = "https://api.xero.com/api.xro/2.0"
    CONNECTIONS_URL = "https://api.xero.com/connections"
    TOKEN_URL = "https://identity.xero.com/connect/token"

    def __init__(
        self,
        access_token: str,
        refresh_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        oauth_token_dict: dict[str, Any] | None = None,
    ):
        """Initialize XeroClient with OAuth credentials.

        Args:
            access_token: OAuth access token
            refresh_token: OAuth refresh token for token refresh
            client_id: OAuth client ID for token refresh
            client_secret: OAuth client secret for token refresh
            oauth_token_dict: Full OAuth token dictionary to store
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self._oauth_token_dict = oauth_token_dict or {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
        self.base_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get_tenants(self) -> list[dict[str, Any]]:
        """Fetch all available Xero tenants/organizations"""
        response = requests.get(self.CONNECTIONS_URL, headers=self.base_headers)

        if response.status_code == 401:
            raise UserException("Authentication failed. Please reconnect your Xero account.")
        elif response.status_code != 200:
            raise UserException(f"Failed to fetch Xero tenants: {response.status_code} - {response.text}")

        return response.json()

    def get_report(self, report_type: str, tenant_id: str, parameters: dict[str, str]) -> dict[str, Any]:
        """
        Fetch a report for a specific tenant.

        Args:
            report_type: The report type or custom report ID
            tenant_id: Xero tenant ID (required for all API calls)
            parameters: Query parameters for the report
        """
        endpoint = f"{self.BASE_URL}/Reports/{report_type}"

        # Add xero-tenant-id header
        headers = self.base_headers.copy()
        headers["xero-tenant-id"] = tenant_id

        response = requests.get(endpoint, headers=headers, params=parameters)

        if response.status_code == 401:
            raise UserException("Authentication failed. Please reconnect your Xero account.")
        elif response.status_code == 403:
            raise UserException("Access forbidden. Check your Xero permissions.")
        elif response.status_code == 404:
            raise UserException(f"Report '{report_type}' not found. Check the report name.")
        elif response.status_code != 200:
            raise UserException(f"Xero API error: {response.status_code} - {response.text}")

        return response.json()

    def refresh_access_token(self) -> None:
        """Refresh the access token using the refresh token."""
        if not self.refresh_token:
            raise UserException("Cannot refresh token: refresh_token not available")
        if not self.client_id or not self.client_secret:
            raise UserException("Cannot refresh token: client_id or client_secret not available")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            token_data = response.json()

            # Update tokens
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data.get("refresh_token", self.refresh_token)

            # Update oauth token dict
            self._oauth_token_dict.update(
                {
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                    "expires_in": token_data.get("expires_in"),
                    "token_type": token_data.get("token_type"),
                }
            )

            # Update headers with new access token
            self.base_headers["Authorization"] = f"Bearer {self.access_token}"

        except requests.exceptions.RequestException as e:
            raise UserException(f"Failed to refresh access token: {str(e)}")

    def get_oauth_token_dict(self) -> dict[str, Any]:
        """Get the current OAuth token dictionary."""
        return self._oauth_token_dict.copy()

    def set_oauth_token_dict(self, token_dict: dict[str, Any]) -> None:
        """Set the OAuth token dictionary and update client credentials."""
        self._oauth_token_dict = token_dict
        if "access_token" in token_dict:
            self.access_token = token_dict["access_token"]
            self.base_headers["Authorization"] = f"Bearer {self.access_token}"
        if "refresh_token" in token_dict:
            self.refresh_token = token_dict["refresh_token"]
