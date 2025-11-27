"""Storage API client for retrieving table metadata."""

import json
import logging
import time
import urllib.request


class SAPIClient:
    """Simple Storage API client for retrieving table details."""

    def __init__(self, base_url: str, sapi_token: str, retry_attempts: int = 3):
        """Initialize SAPI client.

        Args:
            base_url: Storage API base URL
            sapi_token: Storage API token
            retry_attempts: Number of retry attempts for failed requests
        """
        self.base_url = base_url.rstrip("/")
        self.headers = {"X-StorageApi-Token": sapi_token}
        self.retry_attempts = retry_attempts

    def get_table_detail(self, table_id: str) -> dict:
        """Get table detail from Storage API.

        Args:
            table_id: Storage table ID (e.g., 'in.c-bucket.table')

        Returns:
            Dictionary containing table metadata

        Raises:
            Exception: If all retry attempts fail
        """
        url = f"{self.base_url}/v2/storage/tables/{table_id}"
        last_exception = None

        for attempt in range(self.retry_attempts):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req) as response:
                    response_data = response.read().decode("utf-8")
                    return json.loads(response_data)
            except Exception as e:
                last_exception = e
                logging.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(attempt + 1)

        if last_exception is not None:
            raise last_exception
        else:
            raise RuntimeError("All attempts to get table detail failed, but no exception was captured.")


def get_table_columns(table_id: str, storage_url: str, storage_token: str) -> list[dict]:
    """Get column information from a Storage API table.

    Args:
        table_id: Storage table ID
        storage_url: Storage API URL
        storage_token: Storage API token

    Returns:
        List of column dictionaries with name, dtype, and is_primary_key fields
    """
    storage_client = SAPIClient(storage_url, storage_token)
    table_detail = storage_client.get_table_detail(table_id)
    columns = []

    # Check if table is typed (has schema) or legacy (no schema)
    if table_detail.get("isTyped") and table_detail.get("definition"):
        # Typed table with schema
        primary_keys = set(table_detail["definition"].get("primaryKeysNames", []))
        columns_to_process = [
            {
                "name": column["name"],
                "dtype": column["definition"].get("type", "STRING"),
            }
            for column in table_detail["definition"]["columns"]
        ]
    else:
        # Non-typed (legacy) table
        primary_keys = set(table_detail.get("primaryKey", []))
        columns_to_process = [
            {
                "name": col_name,
                "dtype": "STRING",
            }
            for col_name in table_detail.get("columns", [])
        ]

    # Create column info for all columns
    for col_info in columns_to_process:
        columns.append(
            {
                "name": col_info["name"],
                "dtype": col_info["dtype"],
                "is_primary_key": col_info["name"] in primary_keys,
            }
        )

    return columns
