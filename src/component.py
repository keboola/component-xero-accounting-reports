import csv
import logging
from typing import Dict, List, Any

from keboola.component.base import ComponentBase, sync_action
from keboola.component.exceptions import UserException
from keboola.component.sync_actions import SelectElement
from keboola.utils.date import get_past_date

from configuration import Configuration
from xero_client import XeroClient


class Component(ComponentBase):

    def __init__(self):
        super().__init__()
        self.config = Configuration(**self.configuration.parameters)

        access_token = self._get_access_token()
        self.client = XeroClient(access_token)

    def run(self):
        # Initialize configuration with all parameters

        parsed_params = self._parse_date_parameters(self.config.get_all_parameters())

        # Determine which tenants to process
        if self.config.xero_tenant_id:
            # Single tenant specified
            tenant_ids = [self.config.xero_tenant_id]
            logging.info(f"Processing single tenant: {self.config.xero_tenant_id}")
        else:
            # Fetch all available tenants
            logging.info("No tenant ID specified, fetching all available tenants")
            tenants = self.client.get_tenants()
            tenant_ids = [tenant["tenantId"] for tenant in tenants]
            logging.info(f"Found {len(tenant_ids)} tenants to process")

        # Process report for each tenant
        for tenant_id in tenant_ids:
            logging.info(f"Fetching report for tenant: {tenant_id}")
            report_name = self.config.get_report_name()
            report_data = self.client.get_report(report_name, tenant_id, parsed_params)
            self._write_report_to_csv(report_data, self.config.report_type, tenant_id)

    def _get_access_token(self) -> str:
        try:
            oauth_creds = self.configuration.oauth_credentials

            # oauth_credentials.data is already a dict with tokens
            access_token = oauth_creds.data.get("access_token")

            if not access_token:
                raise UserException("OAuth access token not found in credentials")

            return access_token
        except Exception as e:
            raise UserException(f"Failed to retrieve OAuth credentials: {str(e)}")

    def _parse_date_parameters(self, params: Dict[str, str]) -> Dict[str, str]:
        parsed = {}
        date_fields = ["fromDate", "toDate", "date"]

        for key, value in params.items():
            if key in date_fields and value:
                try:
                    # Use keboola.utils.date to handle natural language dates
                    parsed_date = get_past_date(value)
                    if parsed_date:
                        parsed[key] = parsed_date.strftime("%Y-%m-%d")
                        logging.info(f"Parsed date parameter {key}: '{value}' -> '{parsed[key]}'")
                    else:
                        # If parsing fails, assume it's already in correct format
                        parsed[key] = value
                        logging.warning(f"Could not parse date parameter {key}='{value}'. Using as-is.")
                except Exception as e:
                    logging.warning(f"Failed to parse date parameter {key}='{value}': {e}. Using as-is.")
                    parsed[key] = value
            else:
                parsed[key] = value

        return parsed

    def _write_report_to_csv(self, report_data: Dict[str, Any], report_type: str, tenant_id: str):
        reports = report_data.get("Reports", [])
        if not reports:
            logging.warning("No report data returned from Xero API")
            return

        report = reports[0]
        rows = report.get("Rows", [])

        # Convert to long format (unpivoted)
        long_format_data = self._flatten_report_rows_long_format(rows, report_type, tenant_id)

        if not long_format_data:
            logging.warning("No data rows found in report")
            return

        # Use single output file for all periods (long format)
        output_file = f"{report_type}_{tenant_id}.csv"
        table = self.create_out_table_definition(output_file, incremental=False)

        # Define consistent column order for long format
        fieldnames = [
            "xero_tenant_id",
            "report_type",
            "row_type",
            "row_title",
            "period_index",
            "period_label",
            "value",
            "account_id",
        ]

        with open(table.full_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(long_format_data)

        self.write_manifest(table)
        logging.info(f"Written {len(long_format_data)} rows to {output_file}")

    def _flatten_report_rows_long_format(
        self, rows: List[Dict[str, Any]], report_type: str, tenant_id: str, header_values: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Converts Xero report rows into long format (unpivoted).
        Each cell value becomes a separate row with metadata.
        """
        long_format = []

        # Extract header values if not provided
        if header_values is None:
            header_values = []
            for row in rows:
                if row.get("RowType") == "Header":
                    cells = row.get("Cells", [])
                    header_values = [cell.get("Value", "") for cell in cells]
                    break

        for row in rows:
            row_type = row.get("RowType")

            if row_type == "Header":
                continue

            if row_type == "Section":
                section_rows = row.get("Rows", [])
                long_format.extend(
                    self._flatten_report_rows_long_format(section_rows, report_type, tenant_id, header_values)
                )

            elif row_type in ["Row", "SummaryRow"]:
                cells = row.get("Cells", [])
                row_title = row.get("Title", "")

                # First cell often contains the row label/title, not data
                # Check if first cell has account attribute to determine structure
                first_cell = cells[0] if cells else {}
                first_cell_attrs = first_cell.get("Attributes", [])
                has_account_in_first = any(attr.get("Id") == "account" for attr in first_cell_attrs)

                # If first cell has account attribute, it's the row title
                if has_account_in_first and cells:
                    row_title = first_cell.get("Value", row_title)
                    data_cells = cells[1:]  # Skip first cell, start from index 1
                    period_offset = 1
                else:
                    data_cells = cells
                    period_offset = 0

                for idx, cell in enumerate(data_cells):
                    value = cell.get("Value", "")
                    cell_idx = idx + period_offset

                    # Create a row for each cell value
                    long_row = {
                        "xero_tenant_id": tenant_id,
                        "report_type": report_type,
                        "row_type": row_type,
                        "row_title": row_title,
                        "period_index": idx,
                        "period_label": header_values[cell_idx] if cell_idx < len(header_values) else "",
                        "value": value,
                        "account_id": "",
                    }

                    # Extract account ID from first cell if it was the title
                    if has_account_in_first and cells:
                        for attr in first_cell_attrs:
                            if attr.get("Id") == "account":
                                long_row["account_id"] = attr.get("Value", "")
                                break

                    long_format.append(long_row)

        return long_format

    def _fetch_available_tenants(self):
        """
        Internal method to fetch tenants from Xero API.
        Used by both sync action and run method.
        """
        access_token = self._get_access_token()
        client = XeroClient(access_token)
        return client.get_tenants()

    @sync_action("get_tenants")
    def get_tenants(self):
        """Sync action to fetch available Xero tenants for UI dropdown."""
        tenants = self.client.get_tenants()
        logging.info(f"Found {len(tenants)} Xero tenants")
        return [SelectElement(t["tenantId"], f"{t['tenantName']} ({t['tenantType']})") for t in tenants]


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
