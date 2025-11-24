import csv
import json
import logging
from typing import Any, Dict, List

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

        # Collect all data from all tenants
        all_data = []
        for tenant_id in tenant_ids:
            logging.info(f"Fetching report for tenant: {tenant_id}")
            report_name = self.config.get_report_name()
            report_data = self.client.get_report(report_name, tenant_id, parsed_params)
            tenant_data = self._process_report_data(report_data, self.config.report_type, tenant_id)
            all_data.extend(tenant_data)

        # Write all data to a single CSV
        if all_data:
            self._write_data_to_csv(all_data, self.config.report_type)

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
            elif key == "timeframe" and self.config.report_type == "BudgetSummary":
                # BudgetSummary requires timeframe as integer: MONTH=1, QUARTER=3, YEAR=12
                timeframe_map = {"MONTH": 1, "QUARTER": 3, "YEAR": 12}
                if value in timeframe_map:
                    parsed[key] = timeframe_map[value]
                    logging.info(f"Converted timeframe for BudgetSummary: '{value}' -> {parsed[key]}")
                else:
                    parsed[key] = value
            else:
                parsed[key] = value

        return parsed

    def _process_report_data(
        self, report_data: Dict[str, Any], report_type: str, tenant_id: str
    ) -> List[Dict[str, Any]]:
        """Process report data and return flattened rows without writing to file."""
        reports = report_data.get("Reports", [])
        if not reports:
            logging.warning(f"No report data returned from Xero API for tenant {tenant_id}")
            return []

        report = reports[0]
        rows = report.get("Rows", [])

        # Convert to long format (unpivoted)
        long_format_data = self._flatten_report_rows_long_format(rows, report_type, tenant_id)

        if not long_format_data:
            logging.warning(f"No data rows found in report for tenant {tenant_id}")
            return []

        logging.info(f"Processed {len(long_format_data)} rows for tenant {tenant_id}")
        return long_format_data

    def _write_data_to_csv(self, data: List[Dict[str, Any]], report_type: str):
        """Write all collected data to a single CSV file."""
        # Use single output file for all tenants
        output_file = f"{report_type}.csv"
        table = self.create_out_table_definition(output_file, incremental=False)

        # Define consistent column order for long format
        fieldnames = [
            "xero_tenant_id",
            "row_id",
            "row_type",
            "column_index",
            "column_name",
            "value",
            "others",
        ]

        # Convert others dict to JSON string for consistent schema
        output_data = []
        for row in data:
            output_row = {k: v for k, v in row.items() if k != "others"}
            # Serialize others as JSON string
            output_row["others"] = json.dumps(row.get("others", {})) if row.get("others") else ""
            output_data.append(output_row)

        with open(table.full_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(output_data)

        self.write_manifest(table)
        logging.info(f"Written {len(data)} total rows to {output_file}")

    def _flatten_report_rows_long_format(
        self,
        rows: List[Dict[str, Any]],
        report_type: str,
        tenant_id: str,
        header_values: List[str] = None,
        row_id_counter: List[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Converts Xero report rows into long format (unpivoted).
        Each cell value becomes a separate row with metadata.
        """
        long_format = []

        # Initialize row counter if not provided (using list to maintain reference across recursion)
        if row_id_counter is None:
            row_id_counter = [0]

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
                    self._flatten_report_rows_long_format(
                        section_rows, report_type, tenant_id, header_values, row_id_counter
                    )
                )

            elif row_type in ["Row", "SummaryRow"]:
                # Increment row counter for this data row
                current_row_id = row_id_counter[0]
                row_id_counter[0] += 1

                cells = row.get("Cells", [])

                # Collect all other info from the row (excluding RowType and Cells)
                others = {k: v for k, v in row.items() if k not in ["RowType", "Cells"]}

                # Process all cells equally - no special treatment
                for idx, cell in enumerate(cells):
                    value = cell.get("Value", "")

                    # Extract any attributes from the cell
                    cell_attrs = cell.get("Attributes", [])
                    cell_attributes = {}
                    for attr in cell_attrs:
                        attr_id = attr.get("Id", "")
                        attr_value = attr.get("Value", "")
                        if attr_id and attr_value:
                            cell_attributes[attr_id] = attr_value

                    # Create a row for each cell value
                    long_row = {
                        "xero_tenant_id": tenant_id,
                        "row_id": current_row_id,
                        "row_type": row_type,
                        "column_index": idx,
                        "column_name": header_values[idx] if idx < len(header_values) else "",
                        "value": value,
                        "others": {**others, **cell_attributes},
                    }

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
