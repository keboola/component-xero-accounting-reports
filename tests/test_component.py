import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from configuration import RowConfiguration, Parameter  # noqa: E402


class TestConfiguration(unittest.TestCase):

    def test_row_configuration_valid(self):
        config = RowConfiguration(
            report_type="ProfitAndLoss",
            parameters=[
                Parameter(key="fromDate", value="2024-01-01"),
                Parameter(key="toDate", value="2024-01-31")
            ]
        )
        self.assertEqual(config.report_type, "ProfitAndLoss")
        self.assertEqual(len(config.parameters), 2)

    def test_get_all_parameters(self):
        config = RowConfiguration(
            report_type="BalanceSheet",
            parameters=[Parameter(key="date", value="2024-12-31")],
            custom_parameters=[Parameter(key="trackingOptionID", value="123")]
        )
        all_params = config.get_all_parameters()
        self.assertEqual(all_params["date"], "2024-12-31")
        self.assertEqual(all_params["trackingOptionID"], "123")

    def test_custom_report_name_required(self):
        config = RowConfiguration(
            report_type="Custom",
            custom_report_name="MyCustomReport"
        )
        self.assertEqual(config.get_report_name(), "MyCustomReport")

    def test_standard_report_name(self):
        config = RowConfiguration(report_type="TrialBalance")
        self.assertEqual(config.get_report_name(), "TrialBalance")


if __name__ == '__main__':
    unittest.main()
