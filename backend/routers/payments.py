import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from database.connection import engine
from dependencies.auth import get_current_user


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


def get_payment_history(column: str, value: str):
    allowed_columns = {
        "member_id",
        "membership_id",
        "plan_id"
    }

    if column not in allowed_columns:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment history field"
        )

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(f"""
                    SELECT *
                    FROM payments
                    WHERE {column} = :value
                    ORDER BY payment_date, payment_id
                """),
                {"value": value}
            )

            payments = result.mappings().all()

            if not payments:
                raise HTTPException(
                    status_code=404,
                    detail="Payment history not found"
                )

            return [dict(payment) for payment in payments]

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in payments endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )


@router.get("/", dependencies=[Depends(get_current_user)])
def get_all_payments():
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT * FROM payments ORDER BY payment_id")
            )

            payments = result.mappings().all()

            return [dict(payment) for payment in payments]

    except Exception:
        logger.exception("Unexpected error in payments endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )


@router.get(
    "/member/{member_id}",
    dependencies=[Depends(get_current_user)]
)
def get_member_payments(member_id: str):
    return get_payment_history("member_id", member_id)


@router.get(
    "/membership/{membership_id}",
    dependencies=[Depends(get_current_user)]
)
def get_membership_payments(membership_id: str):
    return get_payment_history("membership_id", membership_id)


@router.get(
    "/plan/{plan_id}",
    dependencies=[Depends(get_current_user)]
)
def get_plan_payments(plan_id: str):
    return get_payment_history("plan_id", plan_id)


@router.get("/{payment_id}", dependencies=[Depends(get_current_user)])
def get_payment(payment_id: str):
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT *
                    FROM payments
                    WHERE payment_id = :payment_id
                """),
                {"payment_id": payment_id}
            )

            payment = result.mappings().first()

            if payment is None:
                raise HTTPException(
                    status_code=404,
                    detail="Payment not found"
                )

            return dict(payment)

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in payments endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )
