from keboola.component.exceptions import UserException
from pydantic import BaseModel, Field, ValidationError, model_validator


class Parameter(BaseModel):
    key: str
    value: str | bool | int


class Configuration(BaseModel):
    report_type: str
    xero_tenant_id: str | None = Field(default=None)
    custom_report_id: str | None = Field(default=None)
    incremental: bool = Field(default=False)
    report_parameters: list[Parameter] = Field(default_factory=list)
    custom_parameters: list[Parameter] = Field(default_factory=list)
    parameters: list[Parameter] = Field(default_factory=list)  # Internal merged list
    debug: bool = False

    def __init__(self, **data):
        try:
            super().__init__(**data)
        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise UserException(f"Validation Error: {', '.join(error_messages)}")

    @model_validator(mode="after")
    def merge_parameters(self):
        """Merge report_parameters and custom_parameters into a single parameters list."""
        if not self.parameters:
            self.parameters = self.report_parameters + self.custom_parameters
        return self

    @model_validator(mode="after")
    def validate_custom_report(self):
        if self.report_type == "Custom" and not self.custom_report_id:
            raise UserException("custom_report_id is required when report_type is 'Custom'")
        return self
