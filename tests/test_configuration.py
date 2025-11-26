import unittest

from keboola.component.exceptions import UserException

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
        self.assertIsNone(config.custom_report_id)
        self.assertEqual(len(config.parameters), 0)
        self.assertEqual(len(config.report_parameters), 0)
        self.assertEqual(len(config.custom_parameters), 0)
        self.assertFalse(config.debug)

    def test_configuration_with_report_parameters(self):
        """Test configuration with report parameters"""
        config = Configuration(
            report_type="ProfitAndLoss",
            report_parameters=[{"key": "fromDate", "value": "2024-01-01"}, {"key": "toDate", "value": "2024-01-31"}],
        )
        self.assertEqual(config.report_type, "ProfitAndLoss")
        self.assertEqual(len(config.report_parameters), 2)
        self.assertEqual(len(config.parameters), 2)
        self.assertEqual(config.parameters[0].key, "fromDate")
        self.assertEqual(config.parameters[0].value, "2024-01-01")
        self.assertEqual(config.parameters[1].key, "toDate")
        self.assertEqual(config.parameters[1].value, "2024-01-31")

    def test_configuration_with_custom_parameters(self):
        """Test configuration with custom parameters"""
        config = Configuration(
            report_type="BalanceSheet",
            custom_parameters=[{"key": "trackingOptionID", "value": "123"}, {"key": "customField", "value": "value"}],
        )
        self.assertEqual(len(config.custom_parameters), 2)
        self.assertEqual(len(config.parameters), 2)
        self.assertEqual(config.parameters[0].key, "trackingOptionID")
        self.assertEqual(config.parameters[1].key, "customField")

    def test_configuration_parameter_merging(self):
        """Test that report_parameters and custom_parameters are merged"""
        config = Configuration(
            report_type="TrialBalance",
            report_parameters=[{"key": "date", "value": "2024-12-31"}],
            custom_parameters=[{"key": "trackingOptionID", "value": "456"}],
        )
        self.assertEqual(len(config.parameters), 2)
        # Check that report parameters come first
        self.assertEqual(config.parameters[0].key, "date")
        self.assertEqual(config.parameters[0].value, "2024-12-31")
        # Then custom parameters
        self.assertEqual(config.parameters[1].key, "trackingOptionID")
        self.assertEqual(config.parameters[1].value, "456")

    def test_configuration_with_tenant_id(self):
        """Test configuration with xero_tenant_id"""
        tenant_id = "12345-abcde-67890"
        config = Configuration(report_type="ExecutiveSummary", xero_tenant_id=tenant_id)
        self.assertEqual(config.xero_tenant_id, tenant_id)

    def test_configuration_with_debug_flag(self):
        """Test configuration with debug flag"""
        config = Configuration(report_type="BankSummary", debug=True)
        self.assertTrue(config.debug)

    def test_configuration_custom_report_with_id(self):
        """Test custom report configuration with custom_report_id"""
        config = Configuration(report_type="Custom", custom_report_id="MyCustomReport123")
        self.assertEqual(config.report_type, "Custom")
        self.assertEqual(config.custom_report_id, "MyCustomReport123")

    def test_configuration_custom_report_missing_id(self):
        """Test that custom report without ID raises error"""
        with self.assertRaises(UserException) as context:
            Configuration(report_type="Custom")
        self.assertIn("custom_report_id is required", str(context.exception))

    def test_configuration_with_boolean_parameters(self):
        """Test configuration with boolean parameter values"""
        config = Configuration(
            report_type="ProfitAndLoss",
            report_parameters=[{"key": "standardLayout", "value": True}, {"key": "paymentsOnly", "value": False}],
        )
        self.assertEqual(len(config.parameters), 2)
        self.assertTrue(config.parameters[0].value)
        self.assertFalse(config.parameters[1].value)
        self.assertIsInstance(config.parameters[0].value, bool)
        self.assertIsInstance(config.parameters[1].value, bool)

    def test_configuration_with_integer_parameters(self):
        """Test configuration with integer parameter values"""
        config = Configuration(
            report_type="ProfitAndLoss",
            report_parameters=[{"key": "periods", "value": 12}, {"key": "trackingOption", "value": 1}],
        )
        self.assertEqual(len(config.parameters), 2)
        self.assertEqual(config.parameters[0].value, 12)
        self.assertEqual(config.parameters[1].value, 1)
        self.assertIsInstance(config.parameters[0].value, int)
        self.assertIsInstance(config.parameters[1].value, int)

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
        self.assertEqual(len(config.parameters), 3)
        self.assertIsInstance(config.parameters[0].value, str)
        self.assertIsInstance(config.parameters[1].value, int)
        self.assertIsInstance(config.parameters[2].value, bool)

    def test_configuration_empty_parameters(self):
        """Test configuration with empty parameter lists"""
        config = Configuration(report_type="AgedReceivablesByContact", report_parameters=[], custom_parameters=[])
        self.assertEqual(len(config.parameters), 0)

    def test_configuration_all_fields(self):
        """Test configuration with all fields populated"""
        config = Configuration(
            report_type="Custom",
            xero_tenant_id="tenant-123",
            custom_report_id="CustomReport1",
            report_parameters=[{"key": "date", "value": "2024-01-01"}],
            custom_parameters=[{"key": "customKey", "value": "customValue"}],
            debug=True,
        )
        self.assertEqual(config.report_type, "Custom")
        self.assertEqual(config.xero_tenant_id, "tenant-123")
        self.assertEqual(config.custom_report_id, "CustomReport1")
        self.assertEqual(len(config.parameters), 2)
        self.assertTrue(config.debug)

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
        ]
        for report_type in report_types:
            config = Configuration(report_type=report_type)
            self.assertEqual(config.report_type, report_type)
            self.assertIsNone(config.custom_report_id)

    def test_parameter_merge_preserves_order(self):
        """Test that parameter merging preserves order (report then custom)"""
        config = Configuration(
            report_type="ProfitAndLoss",
            report_parameters=[{"key": "param1", "value": "value1"}, {"key": "param2", "value": "value2"}],
            custom_parameters=[{"key": "param3", "value": "value3"}, {"key": "param4", "value": "value4"}],
        )
        self.assertEqual(config.parameters[0].key, "param1")
        self.assertEqual(config.parameters[1].key, "param2")
        self.assertEqual(config.parameters[2].key, "param3")
        self.assertEqual(config.parameters[3].key, "param4")


if __name__ == "__main__":
    unittest.main()
