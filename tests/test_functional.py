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

    def _load_api_response(self, test_name: str, report_name: str) -> dict:
        """Load API response from JSON file in test directory"""
        test_dir = Path(__file__).parent / "functional" / test_name / "source"
        response_file = test_dir / f"{report_name}_response.json"

        with open(response_file, "r") as f:
            return json.load(f)

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

    @freeze_time("2023-04-02")
    @responses.activate
    def test_profit_and_loss(self):
        """Test ProfitAndLoss report extraction"""
        # Set up test directories
        test_dir = Path(__file__).parent / "functional" / "01_ProfitAndLoss"
        source_dir = test_dir / "source" / "data"
        expected_dir = test_dir / "expected" / "data"

        # Set KBC_DATADIR environment variable
        os.environ["KBC_DATADIR"] = str(source_dir)

        # Mock Xero API responses
        self._mock_xero_api_profit_and_loss()

        # Run the component
        component = Component()
        component.execute_action()

        # Verify output
        output_file = source_dir / "out" / "tables" / "ProfitAndLoss.csv"
        expected_file = expected_dir / "out" / "tables" / "ProfitAndLoss.csv"

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
    def test_balance_sheet(self):
        """Test BalanceSheet report extraction"""
        # Set up test directories
        test_dir = Path(__file__).parent / "functional" / "02_BalanceSheet"
        source_dir = test_dir / "source" / "data"
        expected_dir = test_dir / "expected" / "data"

        # Set KBC_DATADIR environment variable
        os.environ["KBC_DATADIR"] = str(source_dir)

        # Mock Xero API responses
        self._mock_xero_api_balance_sheet()

        # Run the component
        component = Component()
        component.execute_action()

        # Verify output
        output_file = source_dir / "out" / "tables" / "BalanceSheet.csv"
        expected_file = expected_dir / "out" / "tables" / "BalanceSheet.csv"

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

    def _mock_xero_api_profit_and_loss(self):
        """Mock Xero API endpoints for ProfitAndLoss test"""
        self._mock_tenants_endpoint("test-tenant-abc-123")
        api_response = self._load_api_response("01_ProfitAndLoss", "ProfitAndLoss")
        responses.add(
            responses.GET, "https://api.xero.com/api.xro/2.0/Reports/ProfitAndLoss", json=api_response, status=200
        )

    def _mock_xero_api_balance_sheet(self):
        """Mock Xero API endpoints for BalanceSheet test"""
        self._mock_tenants_endpoint("ba45b4b5-ee66-4a7f-83ec-4b463794dcce")
        api_response = self._load_api_response("02_BalanceSheet", "BalanceSheet")
        responses.add(
            responses.GET, "https://api.xero.com/api.xro/2.0/Reports/BalanceSheet", json=api_response, status=200
        )

    @freeze_time("2025-11-24")
    @responses.activate
    def test_trial_balance(self):
        """Test TrialBalance report extraction"""
        test_dir = Path(__file__).parent / "functional" / "03_TrialBalance"
        source_dir = test_dir / "source" / "data"
        expected_dir = test_dir / "expected" / "data"

        os.environ["KBC_DATADIR"] = str(source_dir)

        self._mock_xero_api_trial_balance()

        component = Component()
        component.execute_action()

        output_file = source_dir / "out" / "tables" / "TrialBalance.csv"
        expected_file = expected_dir / "out" / "tables" / "TrialBalance.csv"

        self.assertTrue(output_file.exists(), f"Output file not created: {output_file}")

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

    def _mock_xero_api_trial_balance(self):
        """Mock Xero API endpoints for TrialBalance test"""
        self._mock_tenants_endpoint("ba45b4b5-ee66-4a7f-83ec-4b463794dcce")
        api_response = self._load_api_response("03_TrialBalance", "TrialBalance")
        responses.add(
            responses.GET, "https://api.xero.com/api.xro/2.0/Reports/TrialBalance", json=api_response, status=200
        )

    @freeze_time("2025-11-24")
    @responses.activate
    def test_executive_summary(self):
        """Test ExecutiveSummary report extraction"""
        test_dir = Path(__file__).parent / "functional" / "04_ExecutiveSummary"
        source_dir = test_dir / "source" / "data"
        expected_dir = test_dir / "expected" / "data"

        os.environ["KBC_DATADIR"] = str(source_dir)

        self._mock_xero_api_executive_summary()

        component = Component()
        component.execute_action()

        output_file = source_dir / "out" / "tables" / "ExecutiveSummary.csv"
        expected_file = expected_dir / "out" / "tables" / "ExecutiveSummary.csv"

        self.assertTrue(output_file.exists(), f"Output file not created: {output_file}")

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

    def _mock_xero_api_executive_summary(self):
        """Mock Xero API endpoints for ExecutiveSummary test"""
        self._mock_tenants_endpoint("ba45b4b5-ee66-4a7f-83ec-4b463794dcce")
        api_response = self._load_api_response("04_ExecutiveSummary", "ExecutiveSummary")
        responses.add(
            responses.GET, "https://api.xero.com/api.xro/2.0/Reports/ExecutiveSummary", json=api_response, status=200
        )

    @freeze_time("2025-11-24")
    @responses.activate
    def test_bank_summary(self):
        """Test BankSummary report extraction"""
        test_dir = Path(__file__).parent / "functional" / "05_BankSummary"
        source_dir = test_dir / "source" / "data"
        expected_dir = test_dir / "expected" / "data"

        os.environ["KBC_DATADIR"] = str(source_dir)

        self._mock_xero_api_bank_summary()

        component = Component()
        component.execute_action()

        output_file = source_dir / "out" / "tables" / "BankSummary.csv"
        expected_file = expected_dir / "out" / "tables" / "BankSummary.csv"

        self.assertTrue(output_file.exists(), f"Output file not created: {output_file}")

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

    def _mock_xero_api_bank_summary(self):
        """Mock Xero API endpoints for BankSummary test"""
        self._mock_tenants_endpoint("ba45b4b5-ee66-4a7f-83ec-4b463794dcce")
        api_response = self._load_api_response("05_BankSummary", "BankSummary")
        responses.add(
            responses.GET, "https://api.xero.com/api.xro/2.0/Reports/BankSummary", json=api_response, status=200
        )

    @freeze_time("2025-11-24")
    @responses.activate
    def test_budget_summary(self):
        """Test BudgetSummary report extraction"""
        test_dir = Path(__file__).parent / "functional" / "06_BudgetSummary"
        source_dir = test_dir / "source" / "data"
        expected_dir = test_dir / "expected" / "data"

        os.environ["KBC_DATADIR"] = str(source_dir)

        self._mock_xero_api_budget_summary()

        component = Component()
        component.execute_action()

        output_file = source_dir / "out" / "tables" / "BudgetSummary.csv"
        expected_file = expected_dir / "out" / "tables" / "BudgetSummary.csv"

        self.assertTrue(output_file.exists(), f"Output file not created: {output_file}")

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

    def _mock_xero_api_budget_summary(self):
        """Mock Xero API endpoints for BudgetSummary test"""
        self._mock_tenants_endpoint("ba45b4b5-ee66-4a7f-83ec-4b463794dcce")
        api_response = self._load_api_response("06_BudgetSummary", "BudgetSummary")
        responses.add(
            responses.GET, "https://api.xero.com/api.xro/2.0/Reports/BudgetSummary", json=api_response, status=200
        )

    @freeze_time("2025-11-24")
    @responses.activate
    def test_aged_receivables_by_contact(self):
        """Test AgedReceivablesByContact report extraction"""
        test_dir = Path(__file__).parent / "functional" / "07_AgedReceivablesByContact"
        source_dir = test_dir / "source" / "data"
        expected_dir = test_dir / "expected" / "data"

        os.environ["KBC_DATADIR"] = str(source_dir)

        self._mock_xero_api_aged_receivables_by_contact()

        component = Component()
        component.execute_action()

        output_file = source_dir / "out" / "tables" / "AgedReceivablesByContact.csv"
        expected_file = expected_dir / "out" / "tables" / "AgedReceivablesByContact.csv"

        self.assertTrue(output_file.exists(), f"Output file not created: {output_file}")

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

    def _mock_xero_api_aged_receivables_by_contact(self):
        """Mock Xero API endpoints for AgedReceivablesByContact test"""
        self._mock_tenants_endpoint("ba45b4b5-ee66-4a7f-83ec-4b463794dcce")
        api_response = self._load_api_response("07_AgedReceivablesByContact", "AgedReceivablesByContact")
        responses.add(
            responses.GET,
            "https://api.xero.com/api.xro/2.0/Reports/AgedReceivablesByContact",
            json=api_response,
            status=200,
        )

    @freeze_time("2025-11-24")
    @responses.activate
    def test_aged_payables_by_contact(self):
        """Test AgedPayablesByContact report extraction"""
        test_dir = Path(__file__).parent / "functional" / "08_AgedPayablesByContact"
        source_dir = test_dir / "source" / "data"
        expected_dir = test_dir / "expected" / "data"

        os.environ["KBC_DATADIR"] = str(source_dir)

        self._mock_xero_api_aged_payables_by_contact()

        component = Component()
        component.execute_action()

        output_file = source_dir / "out" / "tables" / "AgedPayablesByContact.csv"
        expected_file = expected_dir / "out" / "tables" / "AgedPayablesByContact.csv"

        self.assertTrue(output_file.exists(), f"Output file not created: {output_file}")

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

    def _mock_xero_api_aged_payables_by_contact(self):
        """Mock Xero API endpoints for AgedPayablesByContact test"""
        self._mock_tenants_endpoint("ba45b4b5-ee66-4a7f-83ec-4b463794dcce")
        api_response = self._load_api_response("08_AgedPayablesByContact", "AgedPayablesByContact")
        responses.add(
            responses.GET,
            "https://api.xero.com/api.xro/2.0/Reports/AgedPayablesByContact",
            json=api_response,
            status=200,
        )


if __name__ == "__main__":
    unittest.main()
