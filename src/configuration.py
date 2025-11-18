import logging
from typing import List, Dict, Optional
from keboola.component.exceptions import UserException
from pydantic import BaseModel, Field, ValidationError


class Parameter(BaseModel):
    key: str
    value: str


class RowConfiguration(BaseModel):
    report_type: str
    custom_report_name: Optional[str] = None
    parameters: List[Parameter] = Field(default_factory=list)
    custom_parameters: List[Parameter] = Field(default_factory=list)

    def get_all_parameters(self) -> Dict[str, str]:
        all_params = {}
        for param in self.parameters:
            all_params[param.key] = param.value
        for param in self.custom_parameters:
            all_params[param.key] = param.value
        return all_params

    def get_report_name(self) -> str:
        if self.report_type == "Custom":
            if not self.custom_report_name:
                raise UserException("Custom report name is required when report_type is 'Custom'")
            return self.custom_report_name
        return self.report_type


class Configuration(BaseModel):
    debug: bool = False

    def __init__(self, **data):
        try:
            super().__init__(**data)
        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise UserException(f"Validation Error: {', '.join(error_messages)}")

        if self.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.debug("Component will run in Debug mode")
