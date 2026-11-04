from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TrainerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: str = Field(max_length=20)
    trainer_name: str | None = Field(default=None, max_length=100)
    dob: date | None = None
    gender: str | None = Field(default=None, max_length=10)
    height: float | None = Field(default=None, gt=0)
    weight: float | None = Field(default=None, gt=0)
    speciality: str | None = Field(default=None, max_length=100)
    qualification: str | None = Field(default=None, max_length=100)
    shift: str | None = Field(default=None, max_length=20)


class TrainerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trainer_name: str | None = Field(default=None, max_length=100)
    dob: date | None = None
    gender: str | None = Field(default=None, max_length=10)
    height: float | None = Field(default=None, gt=0)
    weight: float | None = Field(default=None, gt=0)
    speciality: str | None = Field(default=None, max_length=100)
    qualification: str | None = Field(default=None, max_length=100)
    shift: str | None = Field(default=None, max_length=20)
