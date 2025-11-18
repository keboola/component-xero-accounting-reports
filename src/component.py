"""
Xero Accounting Reports Component.

Extracts accounting reports from Xero via API.
Row-based configuration: each execution processes one report.
"""

import csv
import logging
from datetime import datetime
from typing import Any

from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException
from keboola.utils import parse_datetime_interval

from configuration import ComponentConfiguration, RowConfiguration
from xero_client import XeroClient


class Component(ComponentBase):
    """
    Xero Accounting Reports extractor component.

    Processes ONE report configuration per execution (row-based component).
    OAuth token is provided by Keboola's OAuth component.
    """

    def __init__(self):
        super().__init__()

    def run(self):
        """Main execution - processes ONE report configuration (one row)."""
        try:
            config_data = self._validate_and_get_configuration()
            params = self._parse_date_parameters(config_data["params"])

            report_data = self._fetch_report_from_xero(
                config_data["oauth_token"],
                config_data["xero_tenant_id"],
                config_data["row_config"],
                params,
            )

            self._save_output_table(report_data, config_data["row_config"])

            logging.info(f"Successfully extracted {config_data['row_config'].report_type} report")

        except UserException:
            raise
        except Exception as e:
            logging.exception("Unhandled error during report extraction")
            raise UserException(f"Failed to extract Xero report: {str(e)}")

    def _validate_and_get_configuration(self) -> dict[str, Any]:
        """
        Validate configuration and extract necessary parameters.

        Returns:
            Dictionary with oauth_token, row_config, params, and xero_tenant_id
        """
        # Parse component-level config (OAuth token)
        comp_config = ComponentConfiguration(**self.configuration.parameters)
        oauth_token = comp_config.oatuh

        # Parse row configuration (THIS row's report settings)
        row_config = RowConfiguration(**self.configuration.parameters)

        # Get all parameters (predefined + custom merged)
        params = row_config.get_all_parameters()

        # Extract Xero tenant ID from OAuth configuration
        # The tenant ID should be in the OAuth data structure
        xero_tenant_id = self._get_xero_tenant_id()

        logging.info(f"Processing report: {row_config.report_type}")
        if comp_config.debug:
            logging.debug(f"Row configuration: {row_config}")
            logging.debug(f"Parameters: {params}")

        return {
            "oauth_token": oauth_token,
            "row_config": row_config,
            "params": params,
            "xero_tenant_id": xero_tenant_id,
        }

    def _get_xero_tenant_id(self) -> str:
        """
        Extract Xero tenant ID from OAuth configuration.

        The tenant ID identifies which Xero organization to query.
        It should be provided by the OAuth component.

        Returns:
            Xero tenant ID string

        Raises:
            UserException: If tenant ID is not found
        """
        # Try to get tenant ID from authorization.oauth_api.credentials
        auth_data = self.configuration.parameters.get("authorization", {})
        oauth_api = auth_data.get("oauth_api", {})
        credentials = oauth_api.get("credentials", {})

        # Tenant ID might be in different locations depending on OAuth setup
        # Check common locations
        tenant_id = (
            credentials.get("xero_tenant_id")
            or credentials.get("tenantId")
            or credentials.get("tenant_id")
            or self.configuration.parameters.get("xero_tenant_id")
        )

        if not tenant_id:
            raise UserException("Xero tenant ID not found. Please ensure OAuth is properly configured.")

        logging.debug(f"Using Xero tenant ID: {tenant_id}")
        return tenant_id

    def _parse_date_parameters(self, params: dict[str, str]) -> dict[str, str]:
        """
        Parse date strings using keboola.utils date parser.
        Converts human-readable dates to ISO format (YYYY-MM-DD).

        Examples:
            - "3 days ago" -> "2025-11-10"
            - "yesterday" -> "2025-11-12"
            - "2024-01-01" -> "2024-01-01" (already formatted)

        Args:
            params: Dictionary of parameters (may contain date strings)

        Returns:
            Dictionary with parsed dates in ISO format
        """
        parsed = params.copy()
        date_fields = ["fromDate", "toDate", "date"]

        for field in date_fields:
            if field in parsed and parsed[field]:
                try:
                    # Use keboola.utils to parse the date string
                    parsed_date = parse_datetime_interval(parsed[field])
                    # Convert to YYYY-MM-DD format
                    parsed[field] = parsed_date.strftime("%Y-%m-%d")
                    logging.debug(f"Parsed {field}: '{params[field]}' -> '{parsed[field]}'")
                except Exception as e:
                    logging.warning(f"Could not parse date for {field}: {e}. Using value as-is: '{parsed[field]}'")
                    # If parsing fails, try to use the value as-is
                    # It might already be in the correct format

        return parsed

    def _fetch_report_from_xero(
        self,
        oauth_token: str,
        xero_tenant_id: str,
        row_config: RowConfiguration,
        params: dict[str, str],
    ) -> dict[str, Any]:
        """
        Fetch report data from Xero API.

        Args:
            oauth_token: OAuth 2.0 access token
            xero_tenant_id: Xero organization/tenant ID
            row_config: Row configuration with report type and settings
            params: Parsed parameters for the report

        Returns:
            Report data as dictionary
        """
        xero_client = XeroClient(oauth_token)

        report_data = xero_client.get_report(
            xero_tenant_id=xero_tenant_id,
            report_type=row_config.report_type,
            custom_report_id=row_config.custom_report_id,
            params=params,
        )

        return report_data

    def _save_output_table(self, report_data: dict[str, Any], row_config: RowConfiguration):
        """
        Transform Xero report data to CSV and save.

        Xero reports have a nested structure that needs to be flattened.
        The exact structure varies by report type.

        Args:
            report_data: Report data from Xero API
            row_config: Row configuration with report type
        """
        # Generate output filename
        output_filename = self._generate_output_filename(row_config)

        # Create output table definition
        output_table = self.create_out_table_definition(output_filename, incremental=False)

        # Transform and write report data
        rows = self._transform_report_to_rows(report_data, row_config.report_type)

        if not rows:
            logging.warning(f"No data rows found in report {row_config.report_type}")
            # Still create an empty file with headers
            rows = []

        # Write to CSV
        self._write_csv(output_table.full_path, rows)

        # Save table manifest
        self.write_manifest(output_table)

        logging.info(f"Saved report to {output_filename}")

    @staticmethod
    def _generate_output_filename(row_config: RowConfiguration) -> str:
        """
        Generate output filename based on report configuration.

        Args:
            row_config: Row configuration

        Returns:
            Filename string (e.g., "BalanceSheet_2025-11-13.csv")
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")

        if row_config.report_type == "Custom" and row_config.custom_report_id:
            # Use custom report ID in filename
            safe_id = row_config.custom_report_id.replace("/", "_").replace(" ", "_")
            return f"Custom_{safe_id}_{timestamp}.csv"
        else:
            return f"{row_config.report_type}_{timestamp}.csv"

    def _transform_report_to_rows(self, report_data: dict[str, Any], report_type: str) -> list[dict[str, Any]]:
        """
        Transform Xero report data to flat rows for CSV output.

        Xero reports typically have this structure:
        {
            "reports": [{
                "report_id": "...",
                "report_name": "...",
                "report_titles": [...],
                "report_date": "...",
                "rows": [...]
            }]
        }

        Args:
            report_data: Report data from Xero API
            report_type: Type of report being processed

        Returns:
            List of dictionaries representing CSV rows
        """
        rows = []

        try:
            # Extract the report object
            reports = report_data.get("reports", [])
            if not reports:
                logging.warning("No reports found in response")
                return rows

            report = reports[0]
            report_rows = report.get("rows", [])

            # Add metadata columns
            report_id = report.get("report_id", "")
            report_name = report.get("report_name", "")
            report_date = report.get("report_date", "")

            # Process each row in the report
            for row in report_rows:
                flat_row = self._flatten_report_row(row)
                # Add metadata
                flat_row["report_id"] = report_id
                flat_row["report_name"] = report_name
                flat_row["report_date"] = report_date
                flat_row["report_type"] = report_type
                rows.append(flat_row)

        except Exception as e:
            logging.error(f"Error transforming report data: {e}")
            raise UserException(f"Failed to parse report data: {str(e)}")

        return rows

    def _flatten_report_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """
        Flatten a single report row.

        Xero report rows can have nested structures like:
        {
            "row_type": "Row",
            "cells": [
                {"value": "Account Name"},
                {"value": "1000.00"}
            ],
            "title": "...",
            "rows": [...]  # Nested rows
        }

        Args:
            row: Report row data

        Returns:
            Flattened dictionary
        """
        flat = {}

        # Extract basic fields
        flat["row_type"] = row.get("row_type", "")
        flat["title"] = row.get("title", "")

        # Extract cell values
        cells = row.get("cells", [])
        for i, cell in enumerate(cells):
            cell_value = cell.get("value", "")
            flat[f"cell_{i}"] = cell_value

        # Handle nested rows by concatenating their titles
        nested_rows = row.get("rows", [])
        if nested_rows:
            nested_titles = [r.get("title", "") for r in nested_rows]
            flat["nested_rows"] = " | ".join(nested_titles)

        return flat

    @staticmethod
    def _write_csv(file_path: str, rows: list[dict[str, Any]]):
        """
        Write rows to CSV file.

        Args:
            file_path: Full path to output CSV file
            rows: List of dictionaries to write
        """
        if not rows:
            # Write empty file with no headers if no rows
            with open(file_path, mode="wt", encoding="utf-8", newline="") as f:
                f.write("")
            return

        # Get all unique column names across all rows
        columns = set()
        for row in rows:
            columns.update(row.keys())

        # Sort columns for consistent output
        columns = sorted(columns)

        # Write CSV
        with open(file_path, mode="wt", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)


"""
Main entrypoint
"""
if __name__ == "__main__":
    try:
        comp = Component()
        comp.execute_action()
    except UserException as exc:
        logging.exception(exc)
        exit(1)
    except Exception as exc:
        logging.exception(exc)
        exit(2)
