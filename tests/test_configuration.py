import unittest

from configuration import Configuration


class TestConfiguration(unittest.TestCase):
    """Test cases for Configuration model"""

    def test_configuration_minimal(self):
        """Test configuration with only required fields"""
        config = Configuration(
            report_type="ProfitAndLoss",
            destination={"output_table_name": "ProfitAndLoss", "load_type": "full_load"},
        )
        self.assertEqual(config.report_type, "ProfitAndLoss")
        self.assertIsNone(config.xero_tenant_id)
        self.assertEqual(config.destination.output_table_name, "ProfitAndLoss")
        self.assertEqual(config.destination.load_type, "full_load")
        # All optional params should have default empty values
        self.assertEqual(config.fromDate, "")
        self.assertEqual(config.toDate, "")
        self.assertIsNone(config.periods)

    def test_configuration_with_string_parameters(self):
        """Test configuration with string report parameters"""
        config = Configuration(
            report_type="ProfitAndLoss",
            destination={"output_table_name": "ProfitAndLoss", "load_type": "full_load"},
            fromDate="2024-01-01",
            toDate="2024-01-31",
        )
        self.assertEqual(config.report_type, "ProfitAndLoss")
        self.assertEqual(config.fromDate, "2024-01-01")
        self.assertEqual(config.toDate, "2024-01-31")

    def test_configuration_with_tenant_id(self):
        """Test configuration with xero_tenant_id"""
        tenant_id = "12345-abcde-67890"
        config = Configuration(
            report_type="ExecutiveSummary",
            destination={"output_table_name": "ExecutiveSummary", "load_type": "full_load"},
            xero_tenant_id=tenant_id,
        )
        self.assertEqual(config.xero_tenant_id, tenant_id)

    def test_configuration_with_incremental(self):
        """Test configuration with incremental load type"""
        config = Configuration(
            report_type="BankSummary",
            destination={"output_table_name": "BankSummary", "load_type": "incremental_load"},
        )
        self.assertEqual(config.destination.load_type, "incremental_load")

    def test_configuration_with_boolean_parameters(self):
        """Test configuration with boolean parameter values"""
        config = Configuration(
            report_type="ProfitAndLoss",
            destination={"output_table_name": "ProfitAndLoss", "load_type": "full_load"},
            standardLayout=True,
            paymentsOnly=False,
        )
        self.assertTrue(config.standardLayout)
        self.assertFalse(config.paymentsOnly)
        self.assertIsInstance(config.standardLayout, bool)
        self.assertIsInstance(config.paymentsOnly, bool)

    def test_configuration_with_integer_parameters(self):
        """Test configuration with integer parameter values"""
        config = Configuration(
            report_type="ProfitAndLoss",
            destination={"output_table_name": "ProfitAndLoss", "load_type": "full_load"},
            periods=12,
        )
        self.assertEqual(config.periods, 12)
        self.assertIsInstance(config.periods, int)

    def test_configuration_with_mixed_parameter_types(self):
        """Test configuration with mixed parameter value types"""
        config = Configuration(
            report_type="BudgetSummary",
            destination={"output_table_name": "BudgetSummary", "load_type": "full_load"},
            date="2024-01-01",
            periods=12,
            standardLayout=True,
        )
        self.assertIsInstance(config.date, str)
        self.assertIsInstance(config.periods, int)
        self.assertIsInstance(config.standardLayout, bool)

    def test_configuration_filters_empty_strings(self):
        """Test that empty string parameters are stored"""
        config = Configuration(
            report_type="AgedReceivablesByContact",
            destination={"output_table_name": "AgedReceivablesByContact", "load_type": "full_load"},
            date="2024-01-01",
            fromDate="",
            toDate="",
        )
        self.assertEqual(config.date, "2024-01-01")
        self.assertEqual(config.fromDate, "")
        self.assertEqual(config.toDate, "")

    def test_configuration_filters_none_values(self):
        """Test that None parameter values use defaults"""
        config = Configuration(
            report_type="BankSummary",
            destination={"output_table_name": "BankSummary", "load_type": "full_load"},
            fromDate="2024-01-01",
        )
        self.assertEqual(config.fromDate, "2024-01-01")
        # toDate defaults to empty string when not provided
        self.assertEqual(config.toDate, "")

    def test_configuration_all_fields(self):
        """Test configuration with all fields populated"""
        config = Configuration(
            report_type="TrialBalance",
            destination={"output_table_name": "TrialBalance", "load_type": "incremental_load"},
            xero_tenant_id="tenant-123",
            date="2024-01-01",
        )
        self.assertEqual(config.report_type, "TrialBalance")
        self.assertEqual(config.xero_tenant_id, "tenant-123")
        self.assertEqual(config.date, "2024-01-01")
        self.assertEqual(config.destination.load_type, "incremental_load")

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
                report_type=report_type,
                destination={"output_table_name": report_type, "load_type": "full_load"},
            )
            self.assertEqual(config.report_type, report_type)

    def test_configuration_does_not_include_known_fields_in_parameters(self):
        """Test that all fields are accessible as attributes"""
        config = Configuration(
            report_type="ProfitAndLoss",
            destination={"output_table_name": "ProfitAndLoss", "load_type": "incremental_load"},
            xero_tenant_id="test-tenant",
            fromDate="2024-01-01",
        )
        self.assertEqual(config.report_type, "ProfitAndLoss")
        self.assertEqual(config.destination.load_type, "incremental_load")
        self.assertEqual(config.xero_tenant_id, "test-tenant")
        self.assertEqual(config.fromDate, "2024-01-01")

    def test_configuration_report_with_required_parameter(self):
        """Test report types with required parameters"""
        # TenNinetyNine requires reportYear
        config = Configuration(
            report_type="TenNinetyNine",
            destination={"output_table_name": "TenNinetyNine", "load_type": "full_load"},
            reportYear="2024",
        )
        self.assertEqual(config.reportYear, "2024")

    def test_configuration_profit_and_loss_with_all_parameters(self):
        """Test ProfitAndLoss with comprehensive parameters"""
        config = Configuration(
            report_type="ProfitAndLoss",
            destination={"output_table_name": "ProfitAndLoss", "load_type": "full_load"},
            fromDate="2024-01-01",
            toDate="2024-12-31",
            periods=12,
            timeframe="MONTH",
            trackingCategoryID="cat-1",
            trackingOptionID="opt-1",
            standardLayout=True,
            paymentsOnly=False,
        )
        self.assertEqual(config.fromDate, "2024-01-01")
        self.assertEqual(config.toDate, "2024-12-31")
        self.assertEqual(config.periods, 12)
        self.assertEqual(config.timeframe, "MONTH")
        self.assertEqual(config.trackingCategoryID, "cat-1")
        self.assertEqual(config.trackingOptionID, "opt-1")
        self.assertTrue(config.standardLayout)
        self.assertFalse(config.paymentsOnly)

    def test_configuration_destination_with_empty_output_table_name(self):
        """Test configuration with empty output_table_name defaults correctly"""
        config = Configuration(report_type="BalanceSheet", destination={"load_type": "incremental_load"})
        self.assertEqual(config.report_type, "BalanceSheet")
        self.assertEqual(config.destination.output_table_name, "")
        self.assertEqual(config.destination.load_type, "incremental_load")
        # Test that fallback logic works
        table_name = config.destination.output_table_name or config.report_type
        self.assertEqual(table_name, "BalanceSheet")


if __name__ == "__main__":
    unittest.main()
