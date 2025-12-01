import re
from keboola.component.exceptions import UserException
from pydantic import BaseModel, Field, ValidationError, field_validator


class Destination(BaseModel):
    load_type: str = "full_load"
    primary_keys: list[str] = Field(default_factory=list)


class ReportConfig(BaseModel):
    """Configuration for a single report type."""

    report_type: str

    # Report parameters - all optional with empty defaults
    reportYear: str = ""
    date: str = ""
    fromDate: str = ""
    toDate: str = ""
    contactID: str = ""
    periods: int | None = None
    timeframe: str = ""
    trackingOptionID: str = ""
    trackingCategoryID: str = ""
    trackingOptionID2: str = ""
    trackingCategoryID2: str = ""
    standardLayout: bool | None = None
    paymentsOnly: bool | None = None
    reportID: str = ""


class Configuration(BaseModel):
    # Core configuration
    xero_tenant_ids: str = ""
    reports: list[ReportConfig]
    destination: Destination

    @field_validator("xero_tenant_ids")
    @classmethod
    def validate_tenant_ids(cls, v: str) -> str:
        """Validate that tenant IDs are valid UUIDs if provided."""
        if not v or v.strip() == "":
            return v

        # UUID regex pattern (with or without hyphens)
        uuid_pattern = re.compile(r"^[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}$")

        tenant_ids = [tid.strip() for tid in v.split(",")]
        invalid_ids = [tid for tid in tenant_ids if tid and not uuid_pattern.match(tid)]

        if invalid_ids:
            raise ValueError(
                f"Invalid tenant ID format: {', '.join(invalid_ids)}. "
                "Tenant IDs must be valid UUIDs (e.g., 'abc-123-def' or 'abc123def')."
            )

        return v

    @field_validator("reports")
    @classmethod
    def validate_unique_report_types(cls, v: list[ReportConfig]) -> list[ReportConfig]:
        """Ensure each report type appears only once."""
        report_types = [report.report_type for report in v]
        duplicates = [rt for rt in set(report_types) if report_types.count(rt) > 1]

        if duplicates:
            raise ValueError(
                f"Duplicate report types found: {', '.join(duplicates)}. "
                "Each report type can only be configured once."
            )

        return v

    def get_tenant_ids(self) -> list[str]:
        """Parse and return list of tenant IDs from comma-separated string."""
        if not self.xero_tenant_ids or self.xero_tenant_ids.strip() == "":
            return []
        return [tid.strip() for tid in self.xero_tenant_ids.split(",") if tid.strip()]

    def __init__(self, **data):
        try:
            super().__init__(**data)
        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise UserException(f"Validation Error: {', '.join(error_messages)}")
