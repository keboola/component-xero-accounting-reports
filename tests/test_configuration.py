import unittest

from configuration import Configuration, Parameter


class TestParameter(unittest.TestCase):
    """Test cases for Parameter model"""

    def test_parameter_with_string_value(self):
        param = Parameter(key="fromDate", value="2024-01-01")
        self.assertEqual(param.key, "fromDate")
        self.assertEqual(param.value, "2024-01-01")

    def test_parameter_with_boolean_value(self):
        param = Parameter(key="standardLayout", value=True)
        self.assertEqual(param.key, "standardLayout")
        self.assertEqual(param.value, True)
        self.assertIsInstance(param.value, bool)

    def test_parameter_with_integer_value(self):
        param = Parameter(key="periods", value=12)
        self.assertEqual(param.key, "periods")
        self.assertEqual(param.value, 12)
        self.assertIsInstance(param.value, int)


class TestConfiguration(unittest.TestCase):
    """Test cases for Configuration model"""

    def test_configuration_minimal(self):
        """Test configuration with only required fields"""
        config = Configuration(report_type="ProfitAndLoss")
        self.assertEqual(config.report_type, "ProfitAndLoss")
        self.assertIsNone(config.xero_tenant_id)
        self.assertEqual(len(config.report_parameters), 0)
        self.assertFalse(config.incremental)

    def test_configuration_with_report_parameters(self):
        """Test configuration with report parameters"""
        config = Configuration(
            report_type="ProfitAndLoss",
            report_parameters=[{"key": "fromDate", "value": "2024-01-01"}, {"key": "toDate", "value": "2024-01-31"}],
        )
        self.assertEqual(config.report_type, "ProfitAndLoss")
        self.assertEqual(len(config.report_parameters), 2)
        self.assertEqual(config.report_parameters[0].key, "fromDate")
        self.assertEqual(config.report_parameters[0].value, "2024-01-01")
        self.assertEqual(config.report_parameters[1].key, "toDate")
        self.assertEqual(config.report_parameters[1].value, "2024-01-31")

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
            report_parameters=[{"key": "standardLayout", "value": True}, {"key": "paymentsOnly", "value": False}],
        )
        self.assertEqual(len(config.report_parameters), 2)
        self.assertTrue(config.report_parameters[0].value)
        self.assertFalse(config.report_parameters[1].value)
        self.assertIsInstance(config.report_parameters[0].value, bool)
        self.assertIsInstance(config.report_parameters[1].value, bool)

    def test_configuration_with_integer_parameters(self):
        """Test configuration with integer parameter values"""
        config = Configuration(
            report_type="ProfitAndLoss",
            report_parameters=[{"key": "periods", "value": 12}, {"key": "trackingOption", "value": 1}],
        )
        self.assertEqual(len(config.report_parameters), 2)
        self.assertEqual(config.report_parameters[0].value, 12)
        self.assertEqual(config.report_parameters[1].value, 1)
        self.assertIsInstance(config.report_parameters[0].value, int)
        self.assertIsInstance(config.report_parameters[1].value, int)

    def test_configuration_with_mixed_parameter_types(self):
        """Test configuration with mixed parameter value types"""
        config = Configuration(
            report_type="BudgetSummary",
            report_parameters=[
                {"key": "date", "value": "2024-01-01"},
                {"key": "periods", "value": 12},
                {"key": "standardLayout", "value": True},
            ],
        )
        self.assertEqual(len(config.report_parameters), 3)
        self.assertIsInstance(config.report_parameters[0].value, str)
        self.assertIsInstance(config.report_parameters[1].value, int)
        self.assertIsInstance(config.report_parameters[2].value, bool)

    def test_configuration_empty_parameters(self):
        """Test configuration with empty parameter list"""
        config = Configuration(report_type="AgedReceivablesByContact", report_parameters=[])
        self.assertEqual(len(config.report_parameters), 0)

    def test_configuration_all_fields(self):
        """Test configuration with all fields populated"""
        config = Configuration(
            report_type="TrialBalance",
            xero_tenant_id="tenant-123",
            report_parameters=[{"key": "date", "value": "2024-01-01"}],
            incremental=True,
        )
        self.assertEqual(config.report_type, "TrialBalance")
        self.assertEqual(config.xero_tenant_id, "tenant-123")
        self.assertEqual(len(config.report_parameters), 1)
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


if __name__ == "__main__":
    unittest.main()
