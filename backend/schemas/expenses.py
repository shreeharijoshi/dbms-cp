from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExpenseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expense_id: str = Field(max_length=20)
    expense_type: Literal["Salary", "Maintenance"] | None = None
    trainer_id: str | None = Field(default=None, max_length=20)
    misc_employee_id: str | None = Field(default=None, max_length=20)
    inventory_id: str | None = Field(default=None, max_length=20)
    expense_month: str | None = Field(default=None, max_length=20)
    amount: float | None = Field(default=None, ge=0)
    bonus: float | None = Field(default=None, ge=0)
    payment_date: date | None = None
    payment_mode: Literal["Cash", "Card", "UPI", "Bank Transfer"] | None = None
    remarks: str | None = Field(default=None, max_length=100)


class ExpenseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expense_type: Literal["Salary", "Maintenance"] | None = None
    trainer_id: str | None = Field(default=None, max_length=20)
    misc_employee_id: str | None = Field(default=None, max_length=20)
    inventory_id: str | None = Field(default=None, max_length=20)
    expense_month: str | None = Field(default=None, max_length=20)
    amount: float | None = Field(default=None, ge=0)
    bonus: float | None = Field(default=None, ge=0)
    payment_date: date | None = None
    payment_mode: Literal["Cash", "Card", "UPI", "Bank Transfer"] | None = None
    remarks: str | None = Field(default=None, max_length=100)
