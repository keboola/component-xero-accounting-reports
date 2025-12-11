import re
from keboola.component.exceptions import UserException
from pydantic import BaseModel, Field, ValidationError, field_validator


class Destination(BaseModel):
    output_table_name: str = ""
    load_type: str = "full_load"
    primary_keys: list[str] = Field(default_factory=list)


class ReportConfig(BaseModel):
    """Configuration for a single report type."""

    report_type: str
    destination: Destination = Field(default_factory=Destination)

    # Report parameters - all optional with empty defaults
    reportYear: str = ""
    date: str = ""
    fromDate: str = ""
    toDate: str = ""
    contactID: str = ""
    periods: int = 0
    timeframe: str = ""
    trackingOptionID: str = ""
    trackingCategoryID: str = ""
    trackingOptionID2: str = ""
    trackingCategoryID2: str = ""
    standardLayout: bool = False
    paymentsOnly: bool = False
    reportID: str = ""


class Configuration(BaseModel):
    # Core configuration
    xero_tenant_ids: str = ""
    reports: list[ReportConfig]

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
