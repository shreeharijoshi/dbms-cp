from pydantic import BaseModel, Field
from datetime import date


class MemberCreate(BaseModel):
    member_id: str = Field(max_length=20)
    member_name: str = Field(max_length=100)
    gender: str = Field(max_length=10)
    height: float = Field(gt=0)
    weight: float = Field(gt=0)
    contact: str = Field(max_length=15)
    dob: date
    PT: str = Field(default="No", max_length=20)

class MemberUpdate(BaseModel):
    member_name: str | None = Field(default=None, max_length=100)
    gender: str | None = Field(default=None, max_length=10)
    height: float | None = Field(default=None, gt=0)
    weight: float | None = Field(default=None, gt=0)
    contact: str | None = Field(default=None, max_length=15)
    dob: date | None = None
    PT: str | None = Field(default=None, max_length=20)