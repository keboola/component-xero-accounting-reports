import unittest

from configuration import Configuration


class TestConfiguration(unittest.TestCase):

    def test_configuration_valid(self):
        config = Configuration(
            report_type="ProfitAndLoss",
            parameters=[{"key": "fromDate", "value": "2024-01-01"}, {"key": "toDate", "value": "2024-01-31"}],
        )
        self.assertEqual(config.report_type, "ProfitAndLoss")
        self.assertIsNotNone(config.predefined_parameters)
        self.assertEqual(config.predefined_parameters.fromDate, "2024-01-01")
        self.assertEqual(config.predefined_parameters.toDate, "2024-01-31")

    def test_get_all_parameters(self):
        config = Configuration(
            report_type="BalanceSheet",
            parameters=[{"key": "date", "value": "2024-12-31"}, {"key": "trackingOptionID", "value": "123"}],
        )
        all_params = config.get_all_parameters()
        self.assertEqual(all_params["date"], "2024-12-31")
        self.assertEqual(all_params["trackingOptionID"], "123")

    def test_custom_report_name_required(self):
        config = Configuration(report_type="Custom", custom_report_id="MyCustomReport")
        self.assertEqual(config.get_report_name(), "MyCustomReport")

    def test_standard_report_name(self):
        config = Configuration(report_type="TrialBalance")
        self.assertEqual(config.get_report_name(), "TrialBalance")

    def test_boolean_parameters(self):
        config = Configuration(
            report_type="ProfitAndLoss",
            parameters=[{"key": "standardLayout", "value": True}, {"key": "paymentsOnly", "value": False}],
        )
        all_params = config.get_all_parameters()
        self.assertEqual(all_params["standardLayout"], "true")
        self.assertEqual(all_params["paymentsOnly"], "false")

    def test_integer_parameters(self):
        config = Configuration(report_type="ProfitAndLoss", parameters=[{"key": "periods", "value": 12}])
        all_params = config.get_all_parameters()
        self.assertEqual(all_params["periods"], "12")

    def test_timeframe_enum(self):
        config = Configuration(report_type="ProfitAndLoss", parameters=[{"key": "timeframe", "value": "MONTH"}])
        self.assertEqual(config.predefined_parameters.timeframe, "MONTH")


if __name__ == "__main__":
    unittest.main()
