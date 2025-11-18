"""
Configuration models for Xero Accounting Reports component.

Uses Pydantic for validation and type safety.
"""

import logging
from typing import Optional

from keboola.component.exceptions import UserException
from pydantic import BaseModel, Field, ValidationError, field_validator


class ComponentConfiguration(BaseModel):
    """
    Component-level configuration.
    OAuth token is injected by Keboola's OAuth component.
    """

    oauth_token: str = Field(alias="#oauth_token")
    debug: bool = False

    def __init__(self, **data):
        try:
            super().__init__(**data)
        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise UserException(f"Validation Error: {', '.join(error_messages)}")

        if self.debug:
            logging.debug("Component will run in Debug mode")


class CustomParameter(BaseModel):
    """A single custom parameter key-value pair."""

    key: str
    value: str


class PredefinedParameters(BaseModel):
    """
    Standard parameters that work across most Xero reports.
    All fields are optional - user can choose which parameters to provide.
    """

    fromDate: Optional[str] = None
    toDate: Optional[str] = None
    date: Optional[str] = None
    periods: Optional[int] = None
    timeframe: Optional[str] = None
    trackingOptionID1: Optional[str] = None
    trackingOptionID2: Optional[str] = None
    standardLayout: Optional[bool] = None
    paymentsOnly: Optional[bool] = None


class RowConfiguration(BaseModel):
    """
    Configuration for a single row execution.
    Each row represents one report to extract.
    """

    report_type: str
    custom_report_id: Optional[str] = None
    predefined_parameters: Optional[PredefinedParameters] = None
    custom_parameters: Optional[list[CustomParameter]] = None

    def __init__(self, **data):
        try:
            super().__init__(**data)
        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise UserException(f"Row Configuration Validation Error: {', '.join(error_messages)}")

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v: str) -> str:
        """Validate that report_type is one of the allowed values."""
        allowed_reports = [
            "BalanceSheet",
            "ProfitAndLoss",
            "TrialBalance",
            "BankStatement",
            "BankSummary",
            "AgedReceivablesByContact",
            "AgedPayablesByContact",
            "ExecutiveSummary",
            "BudgetSummary",
            "TenNinetyNine",
            "GST",
            "Custom",
        ]
        if v not in allowed_reports:
            raise ValueError(f"Invalid report_type: {v}. Must be one of: {', '.join(allowed_reports)}")
        return v

    @field_validator("custom_report_id")
    @classmethod
    def validate_custom_report_id(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure custom_report_id is provided when report_type is Custom."""
        # Access report_type from the values being validated
        if "report_type" in info.data and info.data["report_type"] == "Custom":
            if not v:
                raise ValueError("custom_report_id is required when report_type is 'Custom'")
        return v

    def get_all_parameters(self) -> dict[str, str]:
        """
        Merge predefined and custom parameters into a single dict.
        This will be passed to Xero API as query parameters.

        Returns:
            Dictionary of parameter names to values (all strings).
        """
        params: dict[str, str] = {}

        # Add predefined parameters (if they exist and are not None)
        if self.predefined_parameters:
            if self.predefined_parameters.fromDate:
                params["fromDate"] = self.predefined_parameters.fromDate
            if self.predefined_parameters.toDate:
                params["toDate"] = self.predefined_parameters.toDate
            if self.predefined_parameters.date:
                params["date"] = self.predefined_parameters.date
            if self.predefined_parameters.periods is not None:
                params["periods"] = str(self.predefined_parameters.periods)
            if self.predefined_parameters.timeframe:
                params["timeframe"] = self.predefined_parameters.timeframe
            if self.predefined_parameters.trackingOptionID1:
                params["trackingOptionID1"] = self.predefined_parameters.trackingOptionID1
            if self.predefined_parameters.trackingOptionID2:
                params["trackingOptionID2"] = self.predefined_parameters.trackingOptionID2
            if self.predefined_parameters.standardLayout is not None:
                params["standardLayout"] = str(self.predefined_parameters.standardLayout).lower()
            if self.predefined_parameters.paymentsOnly is not None:
                params["paymentsOnly"] = str(self.predefined_parameters.paymentsOnly).lower()

        # Add custom parameters (override predefined if same key)
        if self.custom_parameters:
            for param in self.custom_parameters:
                params[param.key] = param.value

        return params
