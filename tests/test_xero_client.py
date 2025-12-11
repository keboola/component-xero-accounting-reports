import unittest

import responses
from keboola.component.exceptions import UserException

from xero_client import XeroClient


class TestXeroClient(unittest.TestCase):
    """Test cases for XeroClient"""

    def setUp(self):
        """Set up test fixtures"""
        self.access_token = "test_access_token_12345"
        self.client = XeroClient(self.access_token)
        self.tenant_id = "test-tenant-id-123"

    def test_initialization(self):
        """Test XeroClient initialization"""
        client = XeroClient("my_token")
        self.assertEqual(client.access_token, "my_token")
        self.assertIn("Authorization", client.base_headers)
        self.assertEqual(client.base_headers["Authorization"], "Bearer my_token")
        self.assertEqual(client.base_headers["Accept"], "application/json")
        self.assertEqual(client.base_headers["Content-Type"], "application/json")

    def test_base_url(self):
        """Test that BASE_URL is correct"""
        self.assertEqual(XeroClient.BASE_URL, "https://api.xero.com/api.xro/2.0")

    def test_connections_url(self):
        """Test that CONNECTIONS_URL is correct"""
        self.assertEqual(XeroClient.CONNECTIONS_URL, "https://api.xero.com/connections")

    @responses.activate
    def test_get_tenants_success(self):
        """Test successful retrieval of tenants"""
        mock_response = [
            {
                "tenantId": "tenant-1",
                "tenantName": "Company A",
                "tenantType": "ORGANISATION",
            },
            {
                "tenantId": "tenant-2",
                "tenantName": "Company B",
                "tenantType": "ORGANISATION",
            },
        ]

        responses.add(responses.GET, XeroClient.CONNECTIONS_URL, json=mock_response, status=200)

        tenants = self.client.get_tenants()

        self.assertEqual(len(tenants), 2)
        self.assertEqual(tenants[0]["tenantId"], "tenant-1")
        self.assertEqual(tenants[0]["tenantName"], "Company A")
        self.assertEqual(tenants[1]["tenantId"], "tenant-2")
        self.assertEqual(tenants[1]["tenantName"], "Company B")

    @responses.activate
    def test_get_tenants_empty_list(self):
        """Test get_tenants when no tenants are available"""
        responses.add(responses.GET, XeroClient.CONNECTIONS_URL, json=[], status=200)

        tenants = self.client.get_tenants()
        self.assertEqual(len(tenants), 0)

    @responses.activate
    def test_get_tenants_authentication_error(self):
        """Test get_tenants with 401 authentication error"""
        responses.add(
            responses.GET,
            XeroClient.CONNECTIONS_URL,
            json={"error": "Unauthorized"},
            status=401,
        )

        with self.assertRaises(UserException) as context:
            self.client.get_tenants()

        self.assertIn("Authentication failed", str(context.exception))
        self.assertIn("reconnect your Xero account", str(context.exception))

    @responses.activate
    def test_get_tenants_other_error(self):
        """Test get_tenants with non-401 error"""
        responses.add(
            responses.GET,
            XeroClient.CONNECTIONS_URL,
            json={"error": "Internal Server Error"},
            status=500,
        )

        with self.assertRaises(UserException) as context:
            self.client.get_tenants()

        self.assertIn("Failed to fetch Xero tenants", str(context.exception))
        self.assertIn("500", str(context.exception))

    @responses.activate
    def test_get_report_success(self):
        """Test successful report retrieval"""
        report_type = "ProfitAndLoss"
        parameters = {"from_date": "2024-01-01", "to_date": "2024-01-31"}

        mock_response = {
            "Reports": [
                {
                    "ReportID": "ProfitAndLoss",
                    "ReportName": "Profit and Loss",
                    "ReportType": "ProfitAndLoss",
                    "ReportTitles": ["Profit and Loss", "Company A", "January 2024"],
                    "ReportDate": "31 January 2024",
                    "Rows": [],
                }
            ]
        }

        responses.add(
            responses.GET,
            f"{XeroClient.BASE_URL}/Reports/{report_type}",
            json=mock_response,
            status=200,
        )

        result = self.client.get_report(report_type, self.tenant_id, parameters)

        self.assertEqual(len(result["Reports"]), 1)
        self.assertEqual(result["Reports"][0]["ReportID"], "ProfitAndLoss")
        self.assertEqual(result["Reports"][0]["ReportName"], "Profit and Loss")

        # Verify the request was made with correct headers
        self.assertEqual(len(responses.calls), 1)
        request_headers = responses.calls[0].request.headers
        self.assertEqual(request_headers["xero-tenant-id"], self.tenant_id)
        self.assertIn("Bearer", request_headers["Authorization"])

    @responses.activate
    def test_get_report_with_parameters(self):
        """Test get_report includes query parameters"""
        report_type = "BalanceSheet"
        # XeroClient expects camelCase parameters (as converted by component._extract_report_params)
        parameters = {
            "date": "2024-12-31",
            "trackingOptionID": "123",
            "standardLayout": "true",
        }

        mock_response = {"Reports": [{"ReportID": "BalanceSheet", "Rows": []}]}

        responses.add(
            responses.GET,
            f"{XeroClient.BASE_URL}/Reports/{report_type}",
            json=mock_response,
            status=200,
        )

        self.client.get_report(report_type, self.tenant_id, parameters)

        # Verify parameters were sent
        request = responses.calls[0].request
        self.assertIn("date=2024-12-31", request.url)
        self.assertIn("trackingOptionID=123", request.url)
        self.assertIn("standardLayout=true", request.url)

    @responses.activate
    def test_get_report_custom_report_id(self):
        """Test get_report with custom report ID"""
        custom_report_id = "MyCustomReport123"
        parameters = {}

        mock_response = {"Reports": [{"ReportID": custom_report_id, "Rows": []}]}

        responses.add(
            responses.GET,
            f"{XeroClient.BASE_URL}/Reports/{custom_report_id}",
            json=mock_response,
            status=200,
        )

        result = self.client.get_report(custom_report_id, self.tenant_id, parameters)

        self.assertEqual(result["Reports"][0]["ReportID"], custom_report_id)

    @responses.activate
    def test_get_report_authentication_error(self):
        """Test get_report with 401 authentication error"""
        responses.add(
            responses.GET,
            f"{XeroClient.BASE_URL}/Reports/ProfitAndLoss",
            json={"error": "Unauthorized"},
            status=401,
        )

        with self.assertRaises(UserException) as context:
            self.client.get_report("ProfitAndLoss", self.tenant_id, {})

        self.assertIn("Authentication failed", str(context.exception))
        self.assertIn("reconnect your Xero account", str(context.exception))

    @responses.activate
    def test_get_report_forbidden_error(self):
        """Test get_report with 403 forbidden error"""
        responses.add(
            responses.GET,
            f"{XeroClient.BASE_URL}/Reports/ProfitAndLoss",
            json={"error": "Forbidden"},
            status=403,
        )

        with self.assertRaises(UserException) as context:
            self.client.get_report("ProfitAndLoss", self.tenant_id, {})

        self.assertIn("Access forbidden", str(context.exception))
        self.assertIn("permissions", str(context.exception))

    @responses.activate
    def test_get_report_not_found_error(self):
        """Test get_report with 404 not found error"""
        report_type = "InvalidReport"
        responses.add(
            responses.GET,
            f"{XeroClient.BASE_URL}/Reports/{report_type}",
            json={"error": "Not Found"},
            status=404,
        )

        with self.assertRaises(UserException) as context:
            self.client.get_report(report_type, self.tenant_id, {})

        self.assertIn("not found", str(context.exception))
        self.assertIn(report_type, str(context.exception))

    @responses.activate
    def test_get_report_other_error(self):
        """Test get_report with other HTTP error"""
        responses.add(
            responses.GET,
            f"{XeroClient.BASE_URL}/Reports/ProfitAndLoss",
            json={"error": "Bad Request"},
            status=400,
        )

        with self.assertRaises(UserException) as context:
            self.client.get_report("ProfitAndLoss", self.tenant_id, {})

        self.assertIn("Xero API error", str(context.exception))
        self.assertIn("400", str(context.exception))

    @responses.activate
    def test_get_report_empty_parameters(self):
        """Test get_report with empty parameters dictionary"""
        report_type = "TrialBalance"
        mock_response = {"Reports": [{"ReportID": report_type, "Rows": []}]}

        responses.add(
            responses.GET,
            f"{XeroClient.BASE_URL}/Reports/{report_type}",
            json=mock_response,
            status=200,
        )

        result = self.client.get_report(report_type, self.tenant_id, {})
        self.assertIsNotNone(result)
        self.assertIn("Reports", result)

    def test_headers_contain_authorization(self):
        """Test that base_headers contain proper authorization"""
        token = "test_token_xyz"
        client = XeroClient(token)

        self.assertIn("Authorization", client.base_headers)
        self.assertEqual(client.base_headers["Authorization"], f"Bearer {token}")

    @responses.activate
    def test_get_report_tenant_id_in_header(self):
        """Test that tenant ID is properly sent in header"""
        report_type = "ExecutiveSummary"
        tenant_id = "specific-tenant-123"

        mock_response = {"Reports": []}
        responses.add(
            responses.GET,
            f"{XeroClient.BASE_URL}/Reports/{report_type}",
            json=mock_response,
            status=200,
        )

        self.client.get_report(report_type, tenant_id, {})

        # Verify tenant ID header
        request_headers = responses.calls[0].request.headers
        self.assertEqual(request_headers["xero-tenant-id"], tenant_id)

    @responses.activate
    def test_multiple_tenants_different_calls(self):
        """Test that different tenant IDs can be used in separate calls"""
        report_type = "BankSummary"
        tenant_1 = "tenant-001"
        tenant_2 = "tenant-002"

        mock_response = {"Reports": []}
        responses.add(
            responses.GET,
            f"{XeroClient.BASE_URL}/Reports/{report_type}",
            json=mock_response,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{XeroClient.BASE_URL}/Reports/{report_type}",
            json=mock_response,
            status=200,
        )

        self.client.get_report(report_type, tenant_1, {})
        self.client.get_report(report_type, tenant_2, {})

        # Verify different tenant IDs were used
        self.assertEqual(responses.calls[0].request.headers["xero-tenant-id"], tenant_1)
        self.assertEqual(responses.calls[1].request.headers["xero-tenant-id"], tenant_2)


if __name__ == "__main__":
    unittest.main()
