from typing import Dict, Any
import requests
from keboola.component.exceptions import UserException


class XeroClient:
    BASE_URL = "https://api.xero.com/api.xro/2.0"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get_report(self, report_type: str, parameters: Dict[str, str]) -> Dict[str, Any]:
        endpoint = f"{self.BASE_URL}/Reports/{report_type}"
        response = requests.get(endpoint, headers=self.headers, params=parameters)

        if response.status_code == 401:
            raise UserException("Authentication failed. Please reconnect your Xero account.")
        elif response.status_code == 403:
            raise UserException("Access forbidden. Check your Xero permissions.")
        elif response.status_code == 404:
            raise UserException(f"Report '{report_type}' not found. Check the report name.")
        elif response.status_code != 200:
            raise UserException(f"Xero API error: {response.status_code} - {response.text}")

        return response.json()
