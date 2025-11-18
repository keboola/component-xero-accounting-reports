import csv
import logging
from typing import Dict, List, Any

from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException
from keboola.utils import parse_datetime_interval

from configuration import Configuration, RowConfiguration
from xero_client import XeroClient


class Component(ComponentBase):

    def __init__(self):
        super().__init__()

    def run(self):
        Configuration(**self.configuration.parameters)
        row_config = RowConfiguration(**self.configuration.config_data)

        access_token = self._get_access_token()
        client = XeroClient(access_token)

        parsed_params = self._parse_date_parameters(row_config.get_all_parameters())
        report_data = client.get_report(row_config.get_report_name(), parsed_params)

        self._write_report_to_csv(report_data, row_config.report_type)

    def _get_access_token(self) -> str:
        try:
            oauth_data = self.configuration.oauth_credentials
            credentials = oauth_data.get("credentials", {})
            data_str = credentials.get("#data", "{}")

            import json
            data = json.loads(data_str)
            access_token = data.get("access_token")

            if not access_token:
                raise UserException("OAuth access token not found")

            return access_token
        except Exception as e:
            raise UserException(f"Failed to retrieve OAuth credentials: {str(e)}")

    def _parse_date_parameters(self, params: Dict[str, str]) -> Dict[str, str]:
        parsed = {}
        date_fields = ["fromDate", "toDate", "date"]

        for key, value in params.items():
            if key in date_fields:
                try:
                    parsed_date = parse_datetime_interval(value)
                    parsed[key] = parsed_date.strftime("%Y-%m-%d")
                except Exception:
                    parsed[key] = value
            else:
                parsed[key] = value

        return parsed

    def _write_report_to_csv(self, report_data: Dict[str, Any], report_type: str):
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

        output_file = f"{report_type}.csv"
        table = self.create_out_table_definition(output_file, incremental=False)

        with open(table.full_path, mode="w", encoding="utf-8", newline="") as f:
            if flattened_data:
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
