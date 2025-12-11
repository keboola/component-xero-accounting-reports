import csv
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

from freezegun import freeze_time
from keboola.component.exceptions import UserException

from component import CSV_FIELDNAMES, TIMEFRAME_MAP, Component


class TestComponent(unittest.TestCase):
    """Test cases for Component class"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for output
        self.temp_dir = tempfile.mkdtemp()

        # Mock configuration
        self.mock_config_data = {
            "parameters": {
                "xero_tenant_ids": "",
                "reports": [
                    {
                        "report_type": "ProfitAndLoss",
                        "from_date": "2024-01-01",
                        "to_date": "2024-01-31",
                        "destination": {
                            "load_type": "full_load",
                        },
                    }
                ],
            },
            "authorization": {
                "oauth_api": {
                    "credentials": {
                        "#data": json.dumps(
                            {
                                "access_token": "test_access_token",
                                "refresh_token": "test_refresh_token",
                            }
                        ),
                        "appKey": "test_client_id",
                        "#appSecret": "test_client_secret",
                    }
                }
            },
        }

    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up temporary directory
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_mock_oauth(self, include_all=True):
        """Helper to create mock oauth credentials"""
        mock_oauth = MagicMock()
        if include_all:
            mock_oauth.data = {
                "access_token": "test_token",
                "refresh_token": "test_refresh",
            }
            mock_oauth.appKey = "test_client_id"
            mock_oauth.appSecret = "test_client_secret"
        else:
            mock_oauth.data = {"access_token": "test_token"}
        return mock_oauth

    def _create_mock_params(self, report_type, **kwargs):
        """Helper to create mock parameters with destination"""
        report_params = {"report_type": report_type}
        # Extract report-level parameters from kwargs
        report_keys = [
            "report_year",
            "date",
            "from_date",
            "to_date",
            "contact_id",
            "periods",
            "timeframe",
            "tracking_option_id",
            "tracking_category_id",
            "tracking_option_id_2",
            "tracking_category_id_2",
            "standard_layout",
            "payments_only",
            "report_id",
        ]
        for key in report_keys:
            if key in kwargs:
                report_params[key] = kwargs.pop(key)

        # Add destination to report
        report_params["destination"] = {
            "load_type": kwargs.pop("load_type", "full_load"),
            "output_table_name": kwargs.pop("output_table_name", ""),
            "primary_keys": kwargs.pop("primary_keys", []),
        }

        params = {
            "xero_tenant_ids": kwargs.pop("xero_tenant_ids", ""),
            "reports": [report_params],
        }
        params.update(kwargs)
        return params

    @patch("component.XeroClient")
    @patch("component.ComponentBase.__init__")
    def test_component_initialization(self, mock_base_init, mock_xero_client):
        """Test Component initialization"""
        mock_base_init.return_value = None

        with patch.object(Component, "configuration") as mock_configuration:
            with patch.object(Component, "get_state_file", return_value={}):
                mock_configuration.parameters = self.mock_config_data["parameters"]
                mock_configuration.oauth_credentials = self._create_mock_oauth()

                component = Component()

                self.assertIsNotNone(component.config)
                # Verify XeroClient was called with all the new parameters
                mock_xero_client.assert_called_once()
                call_kwargs = mock_xero_client.call_args[1]
                self.assertEqual(call_kwargs["access_token"], "test_token")
                self.assertEqual(call_kwargs["refresh_token"], "test_refresh")

    @patch("component.XeroClient")
    @patch("component.ComponentBase.__init__")
    def test_component_initialization_missing_token(self, mock_base_init, mock_xero_client):
        """Test Component initialization with missing access token"""
        mock_base_init.return_value = None

        with patch.object(Component, "configuration") as mock_configuration:
            with patch.object(Component, "get_state_file", return_value={}):
                mock_configuration.parameters = self.mock_config_data["parameters"]
                mock_oauth = MagicMock()
                mock_oauth.data = {}  # No access_token
                mock_configuration.oauth_credentials = mock_oauth

                with self.assertRaises(UserException) as context:
                    Component()

                self.assertIn("OAuth access token not found", str(context.exception))

    def test_parse_date_parameters_with_natural_language(self):
        """Test _parse_date_parameters with natural language dates"""
        with patch("component.ComponentBase.__init__"):
            with patch.object(Component, "configuration") as mock_configuration:
                with patch.object(Component, "get_state_file", return_value={}):
                    mock_configuration.parameters = self._create_mock_params("ProfitAndLoss")
                    mock_configuration.oauth_credentials = self._create_mock_oauth()

                    component = Component()

                    with freeze_time("2024-02-01"):
                        params = {
                            "fromDate": "7 days ago",
                            "toDate": "today",
                            "otherParam": "value",
                        }

                        parsed = component._parse_date_parameters(params, "ProfitAndLoss")

                        self.assertEqual(parsed["fromDate"], "2024-01-25")
                        self.assertEqual(parsed["toDate"], "2024-02-01")
                        self.assertEqual(parsed["otherParam"], "value")

    def test_parse_date_parameters_with_iso_dates(self):
        """Test _parse_date_parameters with ISO format dates"""
        with patch("component.ComponentBase.__init__"):
            with patch.object(Component, "configuration") as mock_configuration:
                with patch.object(Component, "get_state_file", return_value={}):
                    mock_configuration.parameters = self._create_mock_params("BalanceSheet")
                    mock_configuration.oauth_credentials = self._create_mock_oauth()

                    component = Component()

                    params = {"date": "2024-12-31", "from_date": "2024-01-01"}

                    parsed = component._parse_date_parameters(params, "BalanceSheet")

                    self.assertEqual(parsed["date"], "2024-12-31")
                    self.assertEqual(parsed["from_date"], "2024-01-01")

    def test_parse_date_parameters_timeframe_conversion(self):
        """Test _parse_date_parameters converts BudgetSummary timeframe"""
        with patch("component.ComponentBase.__init__"):
            with patch.object(Component, "configuration") as mock_configuration:
                with patch.object(Component, "get_state_file", return_value={}):
                    mock_configuration.parameters = self._create_mock_params("BudgetSummary")
                    mock_configuration.oauth_credentials = self._create_mock_oauth()

                    component = Component()

                    params = {"timeframe": "MONTH"}
                    parsed = component._parse_date_parameters(params, "BudgetSummary")
                    self.assertEqual(parsed["timeframe"], 1)

                    params = {"timeframe": "QUARTER"}
                    parsed = component._parse_date_parameters(params, "BudgetSummary")
                    self.assertEqual(parsed["timeframe"], 3)

                    params = {"timeframe": "YEAR"}
                    parsed = component._parse_date_parameters(params, "BudgetSummary")
                    self.assertEqual(parsed["timeframe"], 12)

    def test_parse_date_parameters_non_budget_timeframe(self):
        """Test _parse_date_parameters doesn't convert timeframe for non-BudgetSummary"""
        with patch("component.ComponentBase.__init__"):
            with patch.object(Component, "configuration") as mock_configuration:
                with patch.object(Component, "get_state_file", return_value={}):
                    mock_configuration.parameters = self._create_mock_params("ProfitAndLoss")
                    mock_configuration.oauth_credentials = self._create_mock_oauth()

                    component = Component()

                    params = {"timeframe": "MONTH"}
                    parsed = component._parse_date_parameters(params, "ProfitAndLoss")
                    self.assertEqual(parsed["timeframe"], "MONTH")

    def test_flatten_report_rows_long_format_simple(self):
        """Test _flatten_report_rows_long_format with simple data"""
        with patch("component.ComponentBase.__init__"):
            with patch.object(Component, "configuration") as mock_configuration:
                with patch.object(Component, "get_state_file", return_value={}):
                    mock_configuration.parameters = self._create_mock_params("ProfitAndLoss")
                    mock_configuration.oauth_credentials = self._create_mock_oauth()

                    component = Component()

                    rows = [
                        {
                            "RowType": "Header",
                            "Cells": [{"Value": "Account"}, {"Value": "Amount"}],
                        },
                        {
                            "RowType": "Row",
                            "Cells": [{"Value": "Revenue"}, {"Value": "10000"}],
                        },
                    ]

                    result = component._flatten_report_rows_long_format(rows, "ProfitAndLoss", "tenant-123")

                    self.assertEqual(len(result), 2)  # 2 cells
                    self.assertEqual(result[0]["xero_tenant_id"], "tenant-123")
                    self.assertEqual(result[0]["row_id"], 0)
                    self.assertEqual(result[0]["row_type"], "Row")
                    self.assertEqual(result[0]["column_index"], 0)
                    self.assertEqual(result[0]["column_name"], "Account")
                    self.assertEqual(result[0]["value"], "Revenue")

                    self.assertEqual(result[1]["column_index"], 1)
                    self.assertEqual(result[1]["column_name"], "Amount")
                    self.assertEqual(result[1]["value"], "10000")

    def test_flatten_report_rows_with_sections(self):
        """Test _flatten_report_rows_long_format with nested sections"""
        with patch("component.ComponentBase.__init__"):
            with patch.object(Component, "configuration") as mock_configuration:
                with patch.object(Component, "get_state_file", return_value={}):
                    mock_configuration.parameters = self._create_mock_params("BalanceSheet")
                    mock_configuration.oauth_credentials = self._create_mock_oauth()

                    component = Component()

                    rows = [
                        {
                            "RowType": "Header",
                            "Cells": [{"Value": "Account"}, {"Value": "Amount"}],
                        },
                        {
                            "RowType": "Section",
                            "Title": "Assets",
                            "Rows": [
                                {
                                    "RowType": "Row",
                                    "Cells": [{"Value": "Cash"}, {"Value": "5000"}],
                                }
                            ],
                        },
                    ]

                    result = component._flatten_report_rows_long_format(rows, "BalanceSheet", "tenant-456")

                    self.assertEqual(len(result), 2)
                    self.assertEqual(result[0]["value"], "Cash")
                    self.assertEqual(result[1]["value"], "5000")

    def test_flatten_report_rows_with_summary_row(self):
        """Test _flatten_report_rows_long_format with SummaryRow type"""
        with patch("component.ComponentBase.__init__"):
            with patch.object(Component, "configuration") as mock_configuration:
                with patch.object(Component, "get_state_file", return_value={}):
                    mock_configuration.parameters = self._create_mock_params("ProfitAndLoss")
                    mock_configuration.oauth_credentials = self._create_mock_oauth()

                    component = Component()

                    rows = [
                        {
                            "RowType": "Header",
                            "Cells": [{"Value": "Label"}, {"Value": "Total"}],
                        },
                        {
                            "RowType": "SummaryRow",
                            "Cells": [{"Value": "Net Profit"}, {"Value": "25000"}],
                        },
                    ]

                    result = component._flatten_report_rows_long_format(rows, "ProfitAndLoss", "tenant-789")

                    self.assertEqual(len(result), 2)
                    self.assertEqual(result[0]["row_type"], "SummaryRow")
                    self.assertEqual(result[0]["value"], "Net Profit")

    def test_flatten_report_rows_with_cell_attributes(self):
        """Test _flatten_report_rows_long_format with cell attributes"""
        with patch("component.ComponentBase.__init__"):
            with patch.object(Component, "configuration") as mock_configuration:
                with patch.object(Component, "get_state_file", return_value={}):
                    mock_configuration.parameters = self._create_mock_params("TrialBalance")
                    mock_configuration.oauth_credentials = self._create_mock_oauth()

                    component = Component()

                    rows = [
                        {"RowType": "Header", "Cells": [{"Value": "Account"}]},
                        {
                            "RowType": "Row",
                            "Cells": [
                                {
                                    "Value": "Bank Account",
                                    "Attributes": [
                                        {"Id": "account", "Value": "001"},
                                        {"Id": "type", "Value": "BANK"},
                                    ],
                                }
                            ],
                        },
                    ]

                    result = component._flatten_report_rows_long_format(rows, "TrialBalance", "tenant-abc")

                    self.assertEqual(len(result), 1)
                    self.assertIn("account", result[0]["others"])
                    self.assertEqual(result[0]["others"]["account"], "001")
                    self.assertIn("type", result[0]["others"])
                    self.assertEqual(result[0]["others"]["type"], "BANK")

    def test_process_report_data_success(self):
        """Test _process_report_data with valid data"""
        with patch("component.ComponentBase.__init__"):
            with patch.object(Component, "configuration") as mock_configuration:
                with patch.object(Component, "get_state_file", return_value={}):
                    mock_configuration.parameters = self._create_mock_params("ProfitAndLoss")
                    mock_configuration.oauth_credentials = self._create_mock_oauth()

                    component = Component()

                    report_data = {
                        "Reports": [
                            {
                                "ReportID": "ProfitAndLoss",
                                "Rows": [
                                    {
                                        "RowType": "Header",
                                        "Cells": [
                                            {"Value": "Account"},
                                            {"Value": "Total"},
                                        ],
                                    },
                                    {
                                        "RowType": "Row",
                                        "Cells": [
                                            {"Value": "Income"},
                                            {"Value": "50000"},
                                        ],
                                    },
                                ],
                            }
                        ]
                    }

                    result = component._process_report_data(report_data, "ProfitAndLoss", "tenant-123")

                    self.assertIsInstance(result, list)
                    self.assertGreater(len(result), 0)

    def test_process_report_data_no_reports(self):
        """Test _process_report_data with no reports in response"""
        with patch("component.ComponentBase.__init__"):
            with patch.object(Component, "configuration") as mock_configuration:
                with patch.object(Component, "get_state_file", return_value={}):
                    mock_configuration.parameters = self._create_mock_params("BalanceSheet")
                    mock_configuration.oauth_credentials = self._create_mock_oauth()

                    component = Component()

                    report_data = {"Reports": []}

                    result = component._process_report_data(report_data, "BalanceSheet", "tenant-456")

                    self.assertEqual(result, [])

    def test_process_report_data_no_rows(self):
        """Test _process_report_data with no rows in report"""
        with patch("component.ComponentBase.__init__"):
            with patch.object(Component, "configuration") as mock_configuration:
                with patch.object(Component, "get_state_file", return_value={}):
                    mock_configuration.parameters = self._create_mock_params("ExecutiveSummary")
                    mock_configuration.oauth_credentials = self._create_mock_oauth()

                    component = Component()

                    report_data = {"Reports": [{"ReportID": "ExecutiveSummary", "Rows": []}]}

                    result = component._process_report_data(report_data, "ExecutiveSummary", "tenant-789")

                    self.assertEqual(result, [])

    def test_write_data_to_csv(self):
        """Test _write_data_to_csv writes correct CSV format"""
        with patch("component.ComponentBase.__init__"):
            with patch.object(Component, "configuration") as mock_configuration:
                with patch.object(Component, "get_state_file", return_value={}):
                    mock_configuration.parameters = self._create_mock_params("ProfitAndLoss")
                    mock_configuration.oauth_credentials = self._create_mock_oauth()

                    component = Component()

                    # Mock the table creation methods
                    mock_table = Mock()
                    mock_table.full_path = os.path.join(self.temp_dir, "ProfitAndLoss.csv")

                    with patch.object(
                        component,
                        "create_out_table_definition",
                        return_value=mock_table,
                    ):
                        with patch.object(component, "write_manifest"):
                            data = [
                                {
                                    "xero_tenant_id": "tenant-123",
                                    "row_id": 0,
                                    "row_type": "Row",
                                    "column_index": 0,
                                    "column_name": "Account",
                                    "value": "Revenue",
                                    "others": {"account_id": "001"},
                                }
                            ]

                            component._write_data_to_csv(data, component.config.reports[0])

                            # Verify file was created
                            self.assertTrue(os.path.exists(mock_table.full_path))

                            # Read and verify content
                            with open(mock_table.full_path, "r") as f:
                                reader = csv.DictReader(f)
                                rows = list(reader)

                                self.assertEqual(len(rows), 1)
                                self.assertEqual(rows[0]["xero_tenant_id"], "tenant-123")
                                self.assertEqual(rows[0]["row_id"], "0")
                                self.assertEqual(rows[0]["column_name"], "Account")
                                self.assertEqual(rows[0]["value"], "Revenue")
                                # Others should be JSON string
                                others_dict = json.loads(rows[0]["others"])
                                self.assertEqual(others_dict["account_id"], "001")

    def test_write_data_to_csv_empty_others(self):
        """Test _write_data_to_csv with empty others field"""
        with patch("component.ComponentBase.__init__"):
            with patch.object(Component, "configuration") as mock_configuration:
                with patch.object(Component, "get_state_file", return_value={}):
                    mock_configuration.parameters = self._create_mock_params("TrialBalance")
                    mock_configuration.oauth_credentials = self._create_mock_oauth()

                    component = Component()

                    mock_table = Mock()
                    mock_table.full_path = os.path.join(self.temp_dir, "TrialBalance.csv")

                    with patch.object(
                        component,
                        "create_out_table_definition",
                        return_value=mock_table,
                    ):
                        with patch.object(component, "write_manifest"):
                            data = [
                                {
                                    "xero_tenant_id": "tenant-456",
                                    "row_id": 0,
                                    "row_type": "Row",
                                    "column_index": 0,
                                    "column_name": "Description",
                                    "value": "Test",
                                    "others": {},
                                }
                            ]

                            component._write_data_to_csv(data, component.config.reports[0])

                            with open(mock_table.full_path, "r") as f:
                                reader = csv.DictReader(f)
                                rows = list(reader)
                                # Empty dict is treated as falsy, so it becomes empty string
                                self.assertEqual(rows[0]["others"], "")

    def test_csv_fieldnames_constant(self):
        """Test that CSV_FIELDNAMES constant is correct"""
        expected_fields = [
            "xero_tenant_id",
            "row_id",
            "row_type",
            "column_index",
            "column_name",
            "value",
            "others",
            "extracted_at",
        ]
        self.assertEqual(CSV_FIELDNAMES, expected_fields)

    def test_timeframe_map_constant(self):
        """Test that TIMEFRAME_MAP constant is correct"""
        self.assertEqual(TIMEFRAME_MAP["MONTH"], 1)
        self.assertEqual(TIMEFRAME_MAP["QUARTER"], 3)
        self.assertEqual(TIMEFRAME_MAP["YEAR"], 12)


if __name__ == "__main__":
    unittest.main()
