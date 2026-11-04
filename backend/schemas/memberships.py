from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MembershipCreate(BaseModel):
    member_id: str = Field(max_length=20)
    plan_id: str = Field(max_length=20)
    start_date: date = Field(default_factory=date.today)
    payment_mode: Literal["Cash", "Card", "UPI", "Bank Transfer"]


class MembershipRenewal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(max_length=20)
    payment_mode: Literal["Cash", "Card", "UPI", "Bank Transfer"]