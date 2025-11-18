from typing import List, Dict, Optional, Union, Literal
from keboola.component.exceptions import UserException
from pydantic import BaseModel, Field, ValidationError, model_validator


class CustomParameter(BaseModel):
    key: str
    value: Union[str, bool, int]


class PredefinedParameters(BaseModel):
    fromDate: Optional[str] = None
    toDate: Optional[str] = None
    date: Optional[str] = None
    periods: Optional[int] = None
    timeframe: Optional[Literal["MONTH", "QUARTER", "YEAR"]] = None
    standardLayout: Optional[bool] = None
    paymentsOnly: Optional[bool] = None
    contactID: Optional[str] = None
    reportYear: Optional[str] = None
    ReportID: Optional[str] = None


class Configuration(BaseModel):
    report_type: str
    xero_tenant_id: Optional[str] = Field(
        default=None, description="Xero tenant ID. Leave empty to fetch reports for all tenants."
    )
    custom_report_id: Optional[str] = None
    parameters: Optional[List[CustomParameter]] = Field(default=None, description="UI parameter array")
    predefined_parameters: Optional[PredefinedParameters] = Field(default_factory=PredefinedParameters)
    custom_parameters: List[CustomParameter] = Field(default_factory=list)
    debug: bool = False

    def __init__(self, **data):
        # Transform parameters array into predefined_parameters and custom_parameters
        if "parameters" in data and data["parameters"]:
            predefined_keys = {
                "fromDate",
                "toDate",
                "date",
                "periods",
                "timeframe",
                "standardLayout",
                "paymentsOnly",
                "contactID",
                "reportYear",
                "ReportID",
            }
            predefined = {}
            custom = []

            for param in data["parameters"]:
                key = param["key"]
                value = param["value"]
                if key in predefined_keys:
                    predefined[key] = value
                else:
                    custom.append({"key": key, "value": value})

            if predefined:
                data["predefined_parameters"] = predefined
            if custom:
                data["custom_parameters"] = custom

            # Remove the parameters array as it's been processed
            del data["parameters"]

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

    def get_all_parameters(self) -> Dict[str, Union[str, bool, int]]:
        """Merge predefined and custom parameters into a single dict for API calls"""
        params = {}

        # Add predefined parameters if they exist
        if self.predefined_parameters:
            predefined_dict = self.predefined_parameters.model_dump(exclude_none=True)
            for key, value in predefined_dict.items():
                # Convert int/bool to string for API calls if needed, or keep native type
                if isinstance(value, bool):
                    params[key] = "true" if value else "false"
                elif isinstance(value, int):
                    params[key] = str(value)
                else:
                    params[key] = value

        # Add custom parameters
        for param in self.custom_parameters:
            if isinstance(param.value, bool):
                params[param.key] = "true" if param.value else "false"
            elif isinstance(param.value, int):
                params[param.key] = str(param.value)
            else:
                params[param.key] = param.value

        return params

    def get_report_name(self) -> str:
        """Get the report name/ID for the API endpoint"""
        if self.report_type == "Custom":
            return self.custom_report_id
        return self.report_type
