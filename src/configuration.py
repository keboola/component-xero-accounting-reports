from keboola.component.exceptions import UserException
from pydantic import BaseModel, Field, ValidationError


class Destination(BaseModel):
    output_table_name: str = ""
    load_type: str = "full_load"
    primary_keys: str = ""


class Configuration(BaseModel):
    # Core configuration
    report_type: str
    destination: Destination
    xero_tenant_id: str | None = Field(default=None)

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

    def __init__(self, **data):
        try:
            super().__init__(**data)
        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise UserException(f"Validation Error: {', '.join(error_messages)}")
