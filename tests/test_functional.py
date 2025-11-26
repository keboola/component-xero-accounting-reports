from component import Component

import csv
import json
import os
import sys
import unittest
from pathlib import Path

import responses
from freezegun import freeze_time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))


class TestComponent(unittest.TestCase):

    def _setup_test_directories(self, source_dir: Path):
        """Create necessary output directories for tests"""
        output_dir = source_dir / "out" / "tables"
        output_dir.mkdir(parents=True, exist_ok=True)

    def _load_api_response(self, test_name: str, report_name: str) -> dict:
        """Load API response from JSON file in test directory"""
        test_dir = Path(__file__).parent / "functional" / test_name / "source"
        response_file = test_dir / f"{report_name}_response.json"

        with open(response_file, "r") as f:
            return json.load(f)

    def _mock_token_refresh_endpoint(self):
        """Mock the OAuth token refresh endpoint"""
        token_response = {
            "access_token": "mock_refreshed_access_token_123456",
            "refresh_token": "mock_refreshed_refresh_token_654321",
            "expires_in": 1800,
            "token_type": "Bearer",
        }
        responses.add(responses.POST, "https://identity.xero.com/connect/token", json=token_response, status=200)

    def _mock_tenants_endpoint(self, tenant_id: str = "ba45b4b5-ee66-4a7f-83ec-4b463794dcce"):
        """Mock the Xero tenants endpoint"""
        tenants_response = [
            {
                "id": "test-connection-id",
                "tenantId": tenant_id,
                "tenantType": "ORGANISATION",
                "tenantName": "Test Company",
                "createdDateUtc": "2023-01-01T00:00:00.000Z",
                "updatedDateUtc": "2023-01-01T00:00:00.000Z",
            }
        ]

        responses.add(responses.GET, "https://api.xero.com/connections", json=tenants_response, status=200)

    def _mock_xero_report_api(self, test_dir_name: str, report_name: str, tenant_id: str):
        """Generic method to mock Xero API endpoints for any report"""
        self._mock_token_refresh_endpoint()
        self._mock_tenants_endpoint(tenant_id)
        api_response = self._load_api_response(test_dir_name, report_name)
        responses.add(
            responses.GET,
            f"https://api.xero.com/api.xro/2.0/Reports/{report_name}",
            json=api_response,
            status=200,
        )

    def _run_report_test(self, test_dir_name: str, report_name: str, tenant_id: str):
        """Generic method to run a report test"""
        # Set up test directories
        test_dir = Path(__file__).parent / "functional" / test_dir_name
        source_dir = test_dir / "source" / "data"
        expected_dir = test_dir / "expected" / "data"

        # Set KBC_DATADIR environment variable
        os.environ["KBC_DATADIR"] = str(source_dir)

        # Create output directories
        self._setup_test_directories(source_dir)

        # Mock Xero API responses
        self._mock_xero_report_api(test_dir_name, report_name, tenant_id)

        # Run the component
        component = Component()
        component.execute_action()

        # Verify output
        output_file = source_dir / "out" / "tables" / f"{report_name}.csv"
        expected_file = expected_dir / "out" / "tables" / f"{report_name}.csv"

        self.assertTrue(output_file.exists(), f"Output file not created: {output_file}")

        # Compare CSV contents
        with open(output_file, "r") as f:
            output_data = list(csv.DictReader(f))

        with open(expected_file, "r") as f:
            expected_data = list(csv.DictReader(f))

        self.assertEqual(
            len(expected_data),
            len(output_data),
            f"Row count mismatch: expected {len(expected_data)}, got {len(output_data)}",
        )

        for i, (expected_row, output_row) in enumerate(zip(expected_data, output_data)):
            self.assertEqual(expected_row, output_row, f"Row {i} doesn't match expected data")

    @freeze_time("2023-04-02")
    @responses.activate
    def test_profit_and_loss(self):
        """Test ProfitAndLoss report extraction"""
        self._run_report_test("01_ProfitAndLoss", "ProfitAndLoss", "test-tenant-abc-123")

    @freeze_time("2023-04-02")
    @responses.activate
    def test_balance_sheet(self):
        """Test BalanceSheet report extraction"""
        self._run_report_test("02_BalanceSheet", "BalanceSheet", "ba45b4b5-ee66-4a7f-83ec-4b463794dcce")

    @freeze_time("2025-11-24")
    @responses.activate
    def test_trial_balance(self):
        """Test TrialBalance report extraction"""
        self._run_report_test("03_TrialBalance", "TrialBalance", "ba45b4b5-ee66-4a7f-83ec-4b463794dcce")

    @freeze_time("2025-11-24")
    @responses.activate
    def test_executive_summary(self):
        """Test ExecutiveSummary report extraction"""
        self._run_report_test("04_ExecutiveSummary", "ExecutiveSummary", "ba45b4b5-ee66-4a7f-83ec-4b463794dcce")

    @freeze_time("2025-11-24")
    @responses.activate
    def test_bank_summary(self):
        """Test BankSummary report extraction"""
        self._run_report_test("05_BankSummary", "BankSummary", "ba45b4b5-ee66-4a7f-83ec-4b463794dcce")

    @freeze_time("2025-11-24")
    @responses.activate
    def test_budget_summary(self):
        """Test BudgetSummary report extraction"""
        self._run_report_test("06_BudgetSummary", "BudgetSummary", "ba45b4b5-ee66-4a7f-83ec-4b463794dcce")

    @freeze_time("2025-11-24")
    @responses.activate
    def test_aged_receivables_by_contact(self):
        """Test AgedReceivablesByContact report extraction"""
        self._run_report_test(
            "07_AgedReceivablesByContact", "AgedReceivablesByContact", "ba45b4b5-ee66-4a7f-83ec-4b463794dcce"
        )

    @freeze_time("2025-11-24")
    @responses.activate
    def test_aged_payables_by_contact(self):
        """Test AgedPayablesByContact report extraction"""
        self._run_report_test(
            "08_AgedPayablesByContact", "AgedPayablesByContact", "ba45b4b5-ee66-4a7f-83ec-4b463794dcce"
        )


if __name__ == "__main__":
    unittest.main()
