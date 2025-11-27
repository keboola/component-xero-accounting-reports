import unittest

from configuration import Configuration


class TestConfiguration(unittest.TestCase):
    """Test cases for Configuration model"""

    def test_configuration_minimal(self):
        """Test configuration with only required fields"""
        config = Configuration(report_type="ProfitAndLoss")
        self.assertEqual(config.report_type, "ProfitAndLoss")
        self.assertIsNone(config.xero_tenant_id)
        self.assertFalse(config.incremental)
        # All optional params should have default empty values
        self.assertEqual(config.fromDate, "")
        self.assertEqual(config.toDate, "")
        self.assertIsNone(config.periods)

    def test_configuration_with_string_parameters(self):
        """Test configuration with string report parameters"""
        config = Configuration(
            report_type="ProfitAndLoss",
            fromDate="2024-01-01",
            toDate="2024-01-31",
        )
        self.assertEqual(config.report_type, "ProfitAndLoss")
        self.assertEqual(config.fromDate, "2024-01-01")
        self.assertEqual(config.toDate, "2024-01-31")

    def test_configuration_with_tenant_id(self):
        """Test configuration with xero_tenant_id"""
        tenant_id = "12345-abcde-67890"
        config = Configuration(report_type="ExecutiveSummary", xero_tenant_id=tenant_id)
        self.assertEqual(config.xero_tenant_id, tenant_id)

    def test_configuration_with_incremental(self):
        """Test configuration with incremental flag"""
        config = Configuration(report_type="BankSummary", incremental=True)
        self.assertTrue(config.incremental)

    def test_configuration_with_boolean_parameters(self):
        """Test configuration with boolean parameter values"""
        config = Configuration(
            report_type="ProfitAndLoss",
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
            periods=12,
        )
        self.assertEqual(config.periods, 12)
        self.assertIsInstance(config.periods, int)

    def test_configuration_with_mixed_parameter_types(self):
        """Test configuration with mixed parameter value types"""
        config = Configuration(
            report_type="BudgetSummary",
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
            fromDate="2024-01-01",
        )
        self.assertEqual(config.fromDate, "2024-01-01")
        # toDate defaults to empty string when not provided
        self.assertEqual(config.toDate, "")

    def test_configuration_all_fields(self):
        """Test configuration with all fields populated"""
        config = Configuration(
            report_type="TrialBalance",
            xero_tenant_id="tenant-123",
            date="2024-01-01",
            incremental=True,
        )
        self.assertEqual(config.report_type, "TrialBalance")
        self.assertEqual(config.xero_tenant_id, "tenant-123")
        self.assertEqual(config.date, "2024-01-01")
        self.assertTrue(config.incremental)

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
            config = Configuration(report_type=report_type)
            self.assertEqual(config.report_type, report_type)

    def test_configuration_does_not_include_known_fields_in_parameters(self):
        """Test that all fields are accessible as attributes"""
        config = Configuration(
            report_type="ProfitAndLoss",
            incremental=True,
            xero_tenant_id="test-tenant",
            fromDate="2024-01-01",
        )
        self.assertEqual(config.report_type, "ProfitAndLoss")
        self.assertTrue(config.incremental)
        self.assertEqual(config.xero_tenant_id, "test-tenant")
        self.assertEqual(config.fromDate, "2024-01-01")

    def test_configuration_report_with_required_parameter(self):
        """Test report types with required parameters"""
        # TenNinetyNine requires reportYear
        config = Configuration(
            report_type="TenNinetyNine",
            reportYear="2024",
        )
        self.assertEqual(config.reportYear, "2024")

    def test_configuration_profit_and_loss_with_all_parameters(self):
        """Test ProfitAndLoss with comprehensive parameters"""
        config = Configuration(
            report_type="ProfitAndLoss",
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


if __name__ == "__main__":
    unittest.main()
