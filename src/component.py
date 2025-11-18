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

    def run(self):
        # Initialize configuration with all parameters
        config = Configuration(**self.configuration.parameters)

        access_token = self._get_access_token()
        client = XeroClient(access_token)

        parsed_params = self._parse_date_parameters(config.get_all_parameters())

        # Determine which tenants to process
        if config.xero_tenant_id:
            # Single tenant specified
            tenant_ids = [config.xero_tenant_id]
            logging.info(f"Processing single tenant: {config.xero_tenant_id}")
        else:
            # Fetch all available tenants
            logging.info("No tenant ID specified, fetching all available tenants")
            tenants = self._fetch_available_tenants()
            tenant_ids = [tenant["tenantId"] for tenant in tenants]
            logging.info(f"Found {len(tenant_ids)} tenants to process")

        # Process report for each tenant
        for tenant_id in tenant_ids:
            logging.info(f"Fetching report for tenant: {tenant_id}")
            report_data = client.get_report(config.get_report_name(), tenant_id, parsed_params)
            self._write_report_to_csv(report_data, config.report_type, tenant_id)

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

        flattened_data = self._flatten_report_rows(rows)

        if not flattened_data:
            logging.warning("No data rows found in report")
            return

        # Include tenant_id in filename
        output_file = f"{report_type}_{tenant_id}.csv"
        table = self.create_out_table_definition(output_file, incremental=False)

        with open(table.full_path, mode="w", encoding="utf-8", newline="") as f:
            if flattened_data:
                # Add tenant_id to each row
                for row in flattened_data:
                    row["xero_tenant_id"] = tenant_id

                writer = csv.DictWriter(f, fieldnames=flattened_data[0].keys())
                writer.writeheader()
                writer.writerows(flattened_data)

        self.write_manifest(table)
        logging.info(f"Written {len(flattened_data)} rows to {output_file}")

    def _flatten_report_rows(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        flattened = []

        for row in rows:
            row_type = row.get("RowType")

            if row_type == "Header":
                continue

            if row_type == "Section":
                section_rows = row.get("Rows", [])
                flattened.extend(self._flatten_report_rows(section_rows))

            elif row_type in ["Row", "SummaryRow"]:
                cells = row.get("Cells", [])
                row_data = {"RowType": row_type}

                if "Title" in row:
                    row_data["Title"] = row["Title"]

                for idx, cell in enumerate(cells):
                    value = cell.get("Value", "")
                    row_data[f"Column_{idx}"] = value

                    attributes = cell.get("Attributes", [])
                    for attr in attributes:
                        attr_id = attr.get("Id", "")
                        attr_value = attr.get("Value", "")
                        if attr_id:
                            row_data[f"Column_{idx}_{attr_id}"] = attr_value

                flattened.append(row_data)

        return flattened

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
        tenants = self._fetch_available_tenants()
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
