from keboola.component.exceptions import UserException
from pydantic import BaseModel, Field, ValidationError


class Parameter(BaseModel):
    key: str
    value: str | bool | int


class Configuration(BaseModel):
    report_type: str
    incremental: bool = Field(default=False)
    report_parameters: list[Parameter] = Field(default_factory=list)
    xero_tenant_id: str | None = Field(default=None)

    def __init__(self, **data):
        try:
            super().__init__(**data)
        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise UserException(f"Validation Error: {', '.join(error_messages)}")
