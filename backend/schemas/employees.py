from pydantic import BaseModel, ConfigDict, Field


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: str = Field(max_length=20)
    employee_name: str | None = Field(default=None, max_length=100)
    role: str | None = Field(default=None, max_length=50)


class EmployeeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_name: str | None = Field(default=None, max_length=100)
    role: str | None = Field(default=None, max_length=50)
