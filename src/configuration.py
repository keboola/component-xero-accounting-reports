from typing import Optional, Union

from keboola.component.exceptions import UserException
from pydantic import BaseModel, Field, ValidationError, model_validator


class Parameter(BaseModel):
    key: str
    value: Union[str, bool, int]


class Configuration(BaseModel):
    report_type: str
    xero_tenant_id: Optional[str] = Field(default=None)
    custom_report_id: Optional[str] = Field(default=None)
    parameters: list[Parameter] = Field(default_factory=list)
    debug: bool = False

    def __init__(self, **data):
        try:
            super().__init__(**data)
        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise UserException(f"Validation Error: {', '.join(error_messages)}")

    @model_validator(mode="after")
    def validate_custom_report(self):
        if self.report_type == "Custom" and not self.custom_report_id:
            raise UserException("custom_report_id is required when report_type is 'Custom'")
        return self
