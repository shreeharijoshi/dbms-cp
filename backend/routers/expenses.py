import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database.connection import engine
from dependencies.auth import require_roles
from schemas.expenses import ExpenseCreate, ExpenseUpdate


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/expenses",
    tags=["Expenses"]
)


def constraint_error() -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=(
            "Database constraint error. Check that expense_id is unique "
            "and referenced trainer, employee, or inventory IDs exist."
        )
    )


@router.get("/")
def get_all_expenses():
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT * FROM expenses ORDER BY expense_id")
            )

            expenses = result.mappings().all()

            return [dict(expense) for expense in expenses]

    except Exception:
        logger.exception("Unexpected error in expenses endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )


@router.get("/{expense_id}")
def get_expense(expense_id: str):
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT *
                    FROM expenses
                    WHERE expense_id = :expense_id
                """),
                {"expense_id": expense_id}
            )

            expense = result.mappings().first()

            if expense is None:
                raise HTTPException(
                    status_code=404,
                    detail="Expense not found"
                )

            return dict(expense)

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in expenses endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )


@router.post("/", dependencies=[Depends(require_roles("Management"))])
def add_expense(expense: ExpenseCreate):
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO expenses (
                        expense_id,
                        expense_type,
                        trainer_id,
                        misc_employee_id,
                        inventory_id,
                        expense_month,
                        amount,
                        bonus,
                        payment_date,
                        payment_mode,
                        remarks
                    )
                    VALUES (
                        :expense_id,
                        :expense_type,
                        :trainer_id,
                        :misc_employee_id,
                        :inventory_id,
                        :expense_month,
                        :amount,
                        :bonus,
                        :payment_date,
                        :payment_mode,
                        :remarks
                    )
                """),
                expense.model_dump()
            )

            result = connection.execute(
                text("""
                    SELECT *
                    FROM expenses
                    WHERE expense_id = :expense_id
                """),
                {"expense_id": expense.expense_id}
            )

            new_expense = result.mappings().first()

            return {
                "message": "Expense added successfully",
                "expense": dict(new_expense)
            }

    except IntegrityError:
        raise constraint_error()

    except Exception:
        logger.exception("Unexpected error in expenses endpoint.")
        raise HTTPException(
            status_code=400,
            detail="Request could not be completed."
        )


@router.patch(
    "/{expense_id}",
    dependencies=[Depends(require_roles("Management"))]
)
def update_expense(expense_id: str, expense: ExpenseUpdate):
    update_data = expense.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update"
        )

    allowed_fields = {
        "expense_type",
        "trainer_id",
        "misc_employee_id",
        "inventory_id",
        "expense_month",
        "amount",
        "bonus",
        "payment_date",
        "payment_mode",
        "remarks"
    }

    if not set(update_data).issubset(allowed_fields):
        raise HTTPException(
            status_code=400,
            detail="Invalid update fields"
        )

    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    SELECT expense_id
                    FROM expenses
                    WHERE expense_id = :expense_id
                """),
                {"expense_id": expense_id}
            )

            if result.first() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Expense not found"
                )

            set_clause = ", ".join(
                f"{field} = :{field}"
                for field in update_data
            )

            update_data["expense_id"] = expense_id

            connection.execute(
                text(f"""
                    UPDATE expenses
                    SET {set_clause}
                    WHERE expense_id = :expense_id
                """),
                update_data
            )

            result = connection.execute(
                text("""
                    SELECT *
                    FROM expenses
                    WHERE expense_id = :expense_id
                """),
                {"expense_id": expense_id}
            )

            updated_expense = result.mappings().first()

            return {
                "message": "Expense updated successfully",
                "expense": dict(updated_expense)
            }

    except HTTPException:
        raise

    except IntegrityError:
        raise constraint_error()

    except Exception:
        logger.exception("Unexpected error in expenses endpoint.")
        raise HTTPException(
            status_code=400,
            detail="Request could not be completed."
        )


@router.delete(
    "/{expense_id}",
    dependencies=[Depends(require_roles("Management"))]
)
def delete_expense(expense_id: str):
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    SELECT expense_id
                    FROM expenses
                    WHERE expense_id = :expense_id
                """),
                {"expense_id": expense_id}
            )

            if result.first() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Expense not found"
                )

            connection.execute(
                text("""
                    DELETE FROM expenses
                    WHERE expense_id = :expense_id
                """),
                {"expense_id": expense_id}
            )

            return {
                "message": "Expense deleted successfully",
                "expense_id": expense_id
            }

    except HTTPException:
        raise

    except IntegrityError:
        raise constraint_error()

    except Exception:
        logger.exception("Unexpected error in expenses endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )
