import unittest

from keboola.component.exceptions import UserException
from configuration import Configuration


class TestConfiguration(unittest.TestCase):
    """Test cases for Configuration model"""

    def test_configuration_minimal(self):
        """Test configuration with only required fields"""
        config = Configuration(
            reports=[
                {
                    "report_type": "ProfitAndLoss",
                    "destination": {"load_type": "full_load"},
                }
            ],
        )
        self.assertEqual(len(config.reports), 1)
        self.assertEqual(config.reports[0].report_type, "ProfitAndLoss")
        self.assertEqual(config.xero_tenant_ids, "")
        self.assertEqual(config.reports[0].destination.load_type, "full_load")
        # All optional params should have default empty values
        self.assertEqual(config.reports[0].fromDate, "")
        self.assertEqual(config.reports[0].toDate, "")
        self.assertIsNone(config.reports[0].periods)

    def test_configuration_with_string_parameters(self):
        """Test configuration with string report parameters"""
        config = Configuration(
            reports=[
                {
                    "report_type": "ProfitAndLoss",
                    "fromDate": "2024-01-01",
                    "toDate": "2024-01-31",
                    "destination": {"load_type": "full_load"},
                }
            ],
        )
        self.assertEqual(config.reports[0].report_type, "ProfitAndLoss")
        self.assertEqual(config.reports[0].fromDate, "2024-01-01")
        self.assertEqual(config.reports[0].toDate, "2024-01-31")

    def test_configuration_with_tenant_ids(self):
        """Test configuration with xero_tenant_ids"""
        tenant_ids = "12345678-1234-1234-1234-123456789012, 87654321-4321-4321-4321-210987654321"
        config = Configuration(
            xero_tenant_ids=tenant_ids,
            reports=[
                {
                    "report_type": "ExecutiveSummary",
                    "destination": {"load_type": "full_load"},
                }
            ],
        )
        self.assertEqual(config.xero_tenant_ids, tenant_ids)
        parsed_ids = config.get_tenant_ids()
        self.assertEqual(len(parsed_ids), 2)
        self.assertEqual(parsed_ids[0], "12345678-1234-1234-1234-123456789012")
        self.assertEqual(parsed_ids[1], "87654321-4321-4321-4321-210987654321")

    def test_configuration_with_empty_tenant_ids(self):
        """Test configuration with empty xero_tenant_ids"""
        config = Configuration(
            xero_tenant_ids="",
            reports=[
                {
                    "report_type": "BalanceSheet",
                    "destination": {"load_type": "full_load"},
                }
            ],
        )
        self.assertEqual(config.xero_tenant_ids, "")
        self.assertEqual(config.get_tenant_ids(), [])

    def test_configuration_invalid_tenant_id_format(self):
        """Test that invalid tenant ID format raises validation error"""
        with self.assertRaises(UserException) as context:
            Configuration(
                xero_tenant_ids="invalid-id",
                reports=[
                    {
                        "report_type": "ProfitAndLoss",
                        "destination": {"load_type": "full_load"},
                    }
                ],
            )
        self.assertIn("Invalid tenant ID format", str(context.exception))

    def test_configuration_with_incremental(self):
        """Test configuration with incremental load type"""
        config = Configuration(
            reports=[
                {
                    "report_type": "BankSummary",
                    "destination": {"load_type": "incremental_load"},
                }
            ],
        )
        self.assertEqual(config.reports[0].destination.load_type, "incremental_load")

    def test_configuration_with_boolean_parameters(self):
        """Test configuration with boolean parameter values"""
        config = Configuration(
            reports=[
                {
                    "report_type": "ProfitAndLoss",
                    "standardLayout": True,
                    "paymentsOnly": False,
                    "destination": {"load_type": "full_load"},
                }
            ],
        )
        self.assertTrue(config.reports[0].standardLayout)
        self.assertFalse(config.reports[0].paymentsOnly)
        self.assertIsInstance(config.reports[0].standardLayout, bool)
        self.assertIsInstance(config.reports[0].paymentsOnly, bool)

    def test_configuration_with_integer_parameters(self):
        """Test configuration with integer parameter values"""
        config = Configuration(
            reports=[
                {
                    "report_type": "ProfitAndLoss",
                    "periods": 12,
                    "destination": {"load_type": "full_load"},
                }
            ],
        )
        self.assertEqual(config.reports[0].periods, 12)
        self.assertIsInstance(config.reports[0].periods, int)

    def test_configuration_with_mixed_parameter_types(self):
        """Test configuration with mixed parameter value types"""
        config = Configuration(
            reports=[
                {
                    "report_type": "BudgetSummary",
                    "date": "2024-01-01",
                    "periods": 12,
                    "standardLayout": True,
                    "destination": {"load_type": "full_load"},
                }
            ],
        )
        self.assertIsInstance(config.reports[0].date, str)
        self.assertIsInstance(config.reports[0].periods, int)
        self.assertIsInstance(config.reports[0].standardLayout, bool)

    def test_configuration_filters_empty_strings(self):
        """Test that empty string parameters are stored"""
        config = Configuration(
            reports=[
                {
                    "report_type": "AgedReceivablesByContact",
                    "date": "2024-01-01",
                    "fromDate": "",
                    "toDate": "",
                    "destination": {"load_type": "full_load"},
                }
            ],
        )
        self.assertEqual(config.reports[0].date, "2024-01-01")
        self.assertEqual(config.reports[0].fromDate, "")
        self.assertEqual(config.reports[0].toDate, "")

    def test_configuration_filters_none_values(self):
        """Test that None parameter values use defaults"""
        config = Configuration(
            reports=[
                {
                    "report_type": "BankSummary",
                    "fromDate": "2024-01-01",
                    "destination": {"load_type": "full_load"},
                }
            ],
        )
        self.assertEqual(config.reports[0].fromDate, "2024-01-01")
        # toDate defaults to empty string when not provided
        self.assertEqual(config.reports[0].toDate, "")

    def test_configuration_all_fields(self):
        """Test configuration with all fields populated"""
        config = Configuration(
            xero_tenant_ids="12345678-1234-1234-1234-123456789012",
            reports=[
                {
                    "report_type": "TrialBalance",
                    "date": "2024-01-01",
                    "destination": {"load_type": "incremental_load"},
                }
            ],
        )
        self.assertEqual(config.reports[0].report_type, "TrialBalance")
        self.assertEqual(config.xero_tenant_ids, "12345678-1234-1234-1234-123456789012")
        self.assertEqual(config.reports[0].date, "2024-01-01")
        self.assertEqual(config.reports[0].destination.load_type, "incremental_load")

    def test_configuration_multiple_reports(self):
        """Test configuration with multiple reports"""
        config = Configuration(
            reports=[
                {
                    "report_type": "ProfitAndLoss",
                    "fromDate": "2024-01-01",
                    "destination": {"load_type": "full_load"},
                },
                {
                    "report_type": "BalanceSheet",
                    "date": "2024-01-31",
                    "destination": {"load_type": "full_load"},
                },
                {
                    "report_type": "TrialBalance",
                    "destination": {"load_type": "full_load"},
                },
            ],
        )
        self.assertEqual(len(config.reports), 3)
        self.assertEqual(config.reports[0].report_type, "ProfitAndLoss")
        self.assertEqual(config.reports[1].report_type, "BalanceSheet")
        self.assertEqual(config.reports[2].report_type, "TrialBalance")

    def test_configuration_duplicate_report_types(self):
        """Test that duplicate report types are allowed (with different table names)"""
        config = Configuration(
            reports=[
                {
                    "report_type": "ProfitAndLoss",
                    "fromDate": "2024-01-01",
                    "toDate": "2024-03-31",
                    "destination": {
                        "load_type": "full_load",
                        "output_table_name": "ProfitAndLoss_Q1",
                    },
                },
                {
                    "report_type": "BalanceSheet",
                    "destination": {"load_type": "full_load"},
                },
                {
                    "report_type": "ProfitAndLoss",
                    "fromDate": "2024-04-01",
                    "toDate": "2024-06-30",
                    "destination": {
                        "load_type": "full_load",
                        "output_table_name": "ProfitAndLoss_Q2",
                    },
                },
            ],
        )
        self.assertEqual(len(config.reports), 3)
        self.assertEqual(config.reports[0].report_type, "ProfitAndLoss")
        self.assertEqual(config.reports[1].report_type, "BalanceSheet")
        self.assertEqual(config.reports[2].report_type, "ProfitAndLoss")
        self.assertEqual(config.reports[0].destination.output_table_name, "ProfitAndLoss_Q1")
        self.assertEqual(config.reports[2].destination.output_table_name, "ProfitAndLoss_Q2")

    def test_configuration_standard_report_types(self):
        """Test various standard report types"""
        report_types = [
            "ProfitAndLoss",
            "BalanceSheet",
            "TrialBalance",
            "ExecutiveSummary",
            "BankSummary",
            "BudgetSummary",
            "AgedReceivablesByContact",
            "AgedPayablesByContact",
            "TenNinetyNine",
            "BASReport",
            "GSTReport",
        ]
        for report_type in report_types:
            config = Configuration(
                reports=[
                    {
                        "report_type": report_type,
                        "destination": {
                            "output_table_name": report_type,
                            "load_type": "full_load",
                        },
                    }
                ],
            )
            self.assertEqual(config.reports[0].report_type, report_type)

    def test_configuration_does_not_include_known_fields_in_parameters(self):
        """Test that all fields are accessible as attributes"""
        config = Configuration(
            xero_tenant_ids="12345678-1234-1234-1234-123456789012",
            reports=[
                {
                    "report_type": "ProfitAndLoss",
                    "fromDate": "2024-01-01",
                    "destination": {"load_type": "incremental_load"},
                }
            ],
        )
        self.assertEqual(config.reports[0].report_type, "ProfitAndLoss")
        self.assertEqual(config.reports[0].destination.load_type, "incremental_load")
        self.assertEqual(config.xero_tenant_ids, "12345678-1234-1234-1234-123456789012")
        self.assertEqual(config.reports[0].fromDate, "2024-01-01")

    def test_configuration_report_with_required_parameter(self):
        """Test report types with required parameters"""
        # TenNinetyNine requires reportYear
        config = Configuration(
            reports=[
                {
                    "report_type": "TenNinetyNine",
                    "reportYear": "2024",
                    "destination": {"load_type": "full_load"},
                }
            ],
        )
        self.assertEqual(config.reports[0].reportYear, "2024")

    def test_configuration_profit_and_loss_with_all_parameters(self):
        """Test ProfitAndLoss with comprehensive parameters"""
        config = Configuration(
            reports=[
                {
                    "report_type": "ProfitAndLoss",
                    "fromDate": "2024-01-01",
                    "toDate": "2024-12-31",
                    "periods": 12,
                    "timeframe": "MONTH",
                    "trackingCategoryID": "cat-1",
                    "trackingOptionID": "opt-1",
                    "standardLayout": True,
                    "paymentsOnly": False,
                    "destination": {"load_type": "full_load"},
                }
            ],
        )
        report = config.reports[0]
        self.assertEqual(report.fromDate, "2024-01-01")
        self.assertEqual(report.toDate, "2024-12-31")
        self.assertEqual(report.periods, 12)
        self.assertEqual(report.timeframe, "MONTH")
        self.assertEqual(report.trackingCategoryID, "cat-1")
        self.assertEqual(report.trackingOptionID, "opt-1")
        self.assertTrue(report.standardLayout)
        self.assertFalse(report.paymentsOnly)

    def test_configuration_destination_load_type(self):
        """Test configuration destination load type"""
        config = Configuration(
            reports=[
                {
                    "report_type": "BalanceSheet",
                    "destination": {"load_type": "incremental_load"},
                }
            ],
        )
        self.assertEqual(config.reports[0].report_type, "BalanceSheet")
        self.assertEqual(config.reports[0].destination.load_type, "incremental_load")
        # Table name is always the report type
        self.assertEqual(config.reports[0].report_type, "BalanceSheet")


if __name__ == "__main__":
    unittest.main()
