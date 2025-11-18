"""
Xero API client wrapper.
Handles authentication and API calls to Xero Accounting API.
"""

import logging
from typing import Any, Optional

from keboola.component.exceptions import UserException
from xero_python.accounting import AccountingApi
from xero_python.api_client import ApiClient, Configuration
from xero_python.api_client.oauth2 import OAuth2Token


class XeroClient:
    """
    Client for interacting with Xero Accounting API.
    Uses OAuth token provided by Keboola's OAuth component.
    """

    def __init__(self, oauth_token: str):
        """
        Initialize Xero API client with OAuth token.

        Args:
            oauth_token: OAuth 2.0 access token from Keboola OAuth component
        """
        self.oauth_token = oauth_token

        # Configure xero-python client
        api_config = Configuration()
        # Create OAuth2Token with the access token
        oauth2_token = OAuth2Token(access_token=oauth_token)

        self.api_client = ApiClient(configuration=api_config, oauth2_token=oauth2_token)
        self.accounting_api = AccountingApi(self.api_client)

        logging.debug("Xero API client initialized")

    def get_report(
        self,
        xero_tenant_id: str,
        report_type: str,
        custom_report_id: Optional[str] = None,
        params: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        Fetch report data from Xero.

        Args:
            xero_tenant_id: The Xero tenant (organization) ID to query
            report_type: The type of report (e.g., "BalanceSheet", "ProfitAndLoss", "Custom")
            custom_report_id: Required if report_type is "Custom"
            params: Query parameters for the report (fromDate, toDate, etc.)

        Returns:
            Dictionary containing report data from Xero API

        Raises:
            UserException: If API call fails or returns an error
        """
        if params is None:
            params = {}

        try:
            logging.info(f"Fetching {report_type} report from Xero")
            logging.debug(f"Parameters: {params}")

            # Call the appropriate Xero API method based on report type
            if report_type == "BalanceSheet":
                response = self.accounting_api.get_report_balance_sheet(
                    xero_tenant_id=xero_tenant_id,
                    date=params.get("date"),
                    periods=int(params["periods"]) if "periods" in params else None,
                    timeframe=params.get("timeframe"),
                    tracking_option_id1=params.get("trackingOptionID1"),
                    tracking_option_id2=params.get("trackingOptionID2"),
                    standard_layout=self._parse_bool(params.get("standardLayout")),
                    payments_only=self._parse_bool(params.get("paymentsOnly")),
                )
            elif report_type == "ProfitAndLoss":
                response = self.accounting_api.get_report_profit_and_loss(
                    xero_tenant_id=xero_tenant_id,
                    from_date=params.get("fromDate"),
                    to_date=params.get("toDate"),
                    periods=int(params["periods"]) if "periods" in params else None,
                    timeframe=params.get("timeframe"),
                    tracking_category_id=params.get("trackingCategoryID"),
                    tracking_category_id2=params.get("trackingCategoryID2"),
                    tracking_option_id=params.get("trackingOptionID"),
                    tracking_option_id2=params.get("trackingOptionID2"),
                    standard_layout=self._parse_bool(params.get("standardLayout")),
                    payments_only=self._parse_bool(params.get("paymentsOnly")),
                )
            elif report_type == "TrialBalance":
                response = self.accounting_api.get_report_trial_balance(
                    xero_tenant_id=xero_tenant_id,
                    date=params.get("date"),
                    payments_only=self._parse_bool(params.get("paymentsOnly")),
                )
            elif report_type == "BankStatement":
                response = self.accounting_api.get_report_bank_statement(
                    xero_tenant_id=xero_tenant_id,
                    bank_account_id=params.get("bankAccountID", ""),
                    from_date=params.get("fromDate"),
                    to_date=params.get("toDate"),
                )
            elif report_type == "AgedReceivablesByContact":
                response = self.accounting_api.get_report_aged_receivables_by_contact(
                    xero_tenant_id=xero_tenant_id,
                    contact_id=params.get("contactID"),
                    date=params.get("date"),
                    from_date=params.get("fromDate"),
                    to_date=params.get("toDate"),
                )
            elif report_type == "AgedPayablesByContact":
                response = self.accounting_api.get_report_aged_payables_by_contact(
                    xero_tenant_id=xero_tenant_id,
                    contact_id=params.get("contactID"),
                    date=params.get("date"),
                    from_date=params.get("fromDate"),
                    to_date=params.get("toDate"),
                )
            elif report_type == "ExecutiveSummary":
                response = self.accounting_api.get_report_executive_summary(
                    xero_tenant_id=xero_tenant_id, date=params.get("date")
                )
            elif report_type == "BudgetSummary":
                response = self.accounting_api.get_report_budget_summary(
                    xero_tenant_id=xero_tenant_id,
                    date=params.get("date"),
                    periods=int(params["periods"]) if "periods" in params else None,
                    timeframe=int(params["timeframe"]) if "timeframe" in params else None,
                )
            elif report_type == "TenNinetyNine":
                response = self.accounting_api.get_report_ten_ninety_nine(
                    xero_tenant_id=xero_tenant_id, report_year=params.get("reportYear")
                )
            elif report_type == "GST" or report_type == "BankSummary":
                # These reports use the generic get_report_from_id method
                report_id = "GST" if report_type == "GST" else "BankSummary"
                response = self.accounting_api.get_report_from_id(xero_tenant_id=xero_tenant_id, report_id=report_id)
            elif report_type == "Custom":
                if not custom_report_id:
                    raise UserException("custom_report_id is required for Custom reports")
                # Use the generic report endpoint for custom reports
                response = self.accounting_api.get_report_from_id(
                    xero_tenant_id=xero_tenant_id, report_id=custom_report_id
                )
            else:
                raise UserException(f"Unsupported report type: {report_type}")

            logging.info(f"Successfully fetched {report_type} report")
            # Convert response to dictionary
            return response.to_dict() if hasattr(response, "to_dict") else response

        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error fetching report from Xero: {error_msg}")

            # Provide user-friendly error messages
            if "401" in error_msg or "Unauthorized" in error_msg:
                raise UserException("Authentication failed. Please reconnect your Xero account in the OAuth settings.")
            elif "403" in error_msg or "Forbidden" in error_msg:
                raise UserException(
                    "Access denied. Please ensure your Xero account has permission to access this report."
                )
            elif "404" in error_msg or "Not Found" in error_msg:
                raise UserException("Report not found. Please check the report type or custom report ID.")
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                raise UserException("Xero API rate limit exceeded. Please wait a few minutes before trying again.")
            else:
                raise UserException(f"Failed to fetch Xero report: {error_msg}")

    @staticmethod
    def _parse_bool(value: Optional[str]) -> Optional[bool]:
        """
        Parse string boolean value to Python bool.

        Args:
            value: String value ("true", "false", or None)

        Returns:
            Boolean value or None
        """
        if value is None:
            return None
        return value.lower() == "true"
