import unittest

from configuration import Configuration


class TestConfiguration(unittest.TestCase):

    def test_configuration_valid(self):
        config = Configuration(
            report_type="ProfitAndLoss",
            report_parameters=[{"key": "fromDate", "value": "2024-01-01"}, {"key": "toDate", "value": "2024-01-31"}],
        )
        self.assertEqual(config.report_type, "ProfitAndLoss")
        self.assertEqual(len(config.parameters), 2)
        self.assertEqual(config.parameters[0].key, "fromDate")
        self.assertEqual(config.parameters[0].value, "2024-01-01")
        self.assertEqual(config.parameters[1].key, "toDate")
        self.assertEqual(config.parameters[1].value, "2024-01-31")

    def test_get_all_parameters(self):
        config = Configuration(
            report_type="BalanceSheet",
            report_parameters=[{"key": "date", "value": "2024-12-31"}],
            custom_parameters=[{"key": "trackingOptionID", "value": "123"}],
        )
        # Test that parameters are merged
        self.assertEqual(len(config.parameters), 2)
        param_dict = {p.key: p.value for p in config.parameters}
        self.assertEqual(param_dict["date"], "2024-12-31")
        self.assertEqual(param_dict["trackingOptionID"], "123")

    def test_custom_report_name_required(self):
        config = Configuration(report_type="Custom", custom_report_id="MyCustomReport")
        # Test that custom_report_id is set
        self.assertEqual(config.custom_report_id, "MyCustomReport")
        self.assertEqual(config.report_type, "Custom")

    def test_standard_report_name(self):
        config = Configuration(report_type="TrialBalance")
        self.assertEqual(config.report_type, "TrialBalance")

    def test_boolean_parameters(self):
        config = Configuration(
            report_type="ProfitAndLoss",
            report_parameters=[{"key": "standardLayout", "value": True}, {"key": "paymentsOnly", "value": False}],
        )
        # Test that boolean values are preserved
        self.assertEqual(len(config.parameters), 2)
        self.assertEqual(config.parameters[0].value, True)
        self.assertEqual(config.parameters[1].value, False)

    def test_integer_parameters(self):
        config = Configuration(report_type="ProfitAndLoss", report_parameters=[{"key": "periods", "value": 12}])
        # Test that integer values are preserved
        self.assertEqual(len(config.parameters), 1)
        self.assertEqual(config.parameters[0].value, 12)
        self.assertIsInstance(config.parameters[0].value, int)

    def test_timeframe_enum(self):
        config = Configuration(report_type="ProfitAndLoss", report_parameters=[{"key": "timeframe", "value": "MONTH"}])
        self.assertEqual(len(config.parameters), 1)
        self.assertEqual(config.parameters[0].key, "timeframe")
        self.assertEqual(config.parameters[0].value, "MONTH")

    def test_parameter_merging(self):
        """Test that report_parameters and custom_parameters are merged into parameters"""
        config = Configuration(
            report_type="ProfitAndLoss",
            report_parameters=[{"key": "fromDate", "value": "2024-01-01"}],
            custom_parameters=[{"key": "customParam", "value": "customValue"}],
        )
        self.assertEqual(len(config.parameters), 2)
        self.assertEqual(config.parameters[0].key, "fromDate")
        self.assertEqual(config.parameters[1].key, "customParam")


if __name__ == "__main__":
    unittest.main()
