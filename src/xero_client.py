from typing import Any, Dict, List

import requests
from keboola.component.exceptions import UserException


class XeroClient:
    BASE_URL = "https://api.xero.com/api.xro/2.0"
    CONNECTIONS_URL = "https://api.xero.com/connections"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get_tenants(self) -> List[Dict[str, Any]]:
        """Fetch all available Xero tenants/organizations"""
        response = requests.get(self.CONNECTIONS_URL, headers=self.base_headers)

        if response.status_code == 401:
            raise UserException("Authentication failed. Please reconnect your Xero account.")
        elif response.status_code != 200:
            raise UserException(f"Failed to fetch Xero tenants: {response.status_code} - {response.text}")

        return response.json()

    def get_report(self, report_type: str, tenant_id: str, parameters: Dict[str, str]) -> Dict[str, Any]:
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
