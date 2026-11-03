import secrets
from datetime import date, timedelta
from calendar import monthrange

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from database.connection import engine
from schemas.memberships import MembershipCreate


router = APIRouter(prefix="/memberships", tags=["Memberships"])


def calculate_end_date(start_date: date, duration: int) -> date:
    """
    Calculate the membership end date.
    The end date is one day before the same date after the plan duration.
    """

    month_index = start_date.year * 12 + start_date.month - 1 + duration

    year, month_index = divmod(month_index, 12)
    month = month_index + 1

    day = min(start_date.day, monthrange(year, month)[1])

    return date(year, month, day) - timedelta(days=1)


def generate_id(prefix: str) -> str:
    """
    Generate a unique-looking membership or payment ID.
    """

    date_part = date.today().strftime("%y%m%d")
    random_part = secrets.token_hex(5).upper()

    return f"{prefix}{date_part}{random_part}"


@router.post("/")
def register_membership(membership: MembershipCreate):

    try:
        with engine.begin() as connection:

            # 1. Check whether the member exists.
            member = connection.execute(
                text("""
                    SELECT member_status
                    FROM members
                    WHERE member_id = :member_id
                    FOR UPDATE
                """),
                {"member_id": membership.member_id}
            ).mappings().first()

            if not member:
                raise HTTPException(
                    status_code=404,
                    detail="Member not found."
                )

            # 2. Check whether the member is active.
            if member["member_status"] != "Active":
                raise HTTPException(
                    status_code=400,
                    detail="Inactive members cannot register for a membership."
                )

            # 3. Check for an existing active membership.
            existing_membership = connection.execute(
                text("""
                    SELECT membership_id, end_date
                    FROM members_plans
                    WHERE member_id = :member_id
                    AND membership_status = 'Active'
                    AND end_date >= :today
                    LIMIT 1
                """),
                {
                    "member_id": membership.member_id,
                    "today": date.today()
                }
            ).mappings().first()

            if existing_membership:
                raise HTTPException(
                    status_code=400,
                    detail="Member already has an active membership."
                )

            # 4. Check whether the selected plan exists.
            plan = connection.execute(
                text("""
                    SELECT duration, price
                    FROM membership_plans
                    WHERE plan_id = :plan_id
                """),
                {"plan_id": membership.plan_id}
            ).mappings().first()

            if not plan:
                raise HTTPException(
                    status_code=404,
                    detail="Membership plan not found."
                )

            # 5. Generate IDs.
            membership_id = generate_id("MSH")
            payment_id = generate_id("PAY")

            # 6. Calculate the membership end date.
            start_date = membership.start_date

            end_date = calculate_end_date(
                start_date,
                plan["duration"]
            )

            # 7. Get the payment amount from the selected plan.
            amount = plan["price"]

            # 8. Insert the membership.
            connection.execute(
                text("""
                    INSERT INTO members_plans (
                        membership_id,
                        member_id,
                        plan_id,
                        start_date,
                        end_date,
                        membership_status
                    )
                    VALUES (
                        :membership_id,
                        :member_id,
                        :plan_id,
                        :start_date,
                        :end_date,
                        'Active'
                    )
                """),
                {
                    "membership_id": membership_id,
                    "member_id": membership.member_id,
                    "plan_id": membership.plan_id,
                    "start_date": start_date,
                    "end_date": end_date
                }
            )

            # 9. Insert the payment.
            connection.execute(
                text("""
                    INSERT INTO payments (
                        payment_id,
                        membership_id,
                        member_id,
                        plan_id,
                        amount,
                        payment_date,
                        payment_mode
                    )
                    VALUES (
                        :payment_id,
                        :membership_id,
                        :member_id,
                        :plan_id,
                        :amount,
                        :payment_date,
                        :payment_mode
                    )
                """),
                {
                    "payment_id": payment_id,
                    "membership_id": membership_id,
                    "member_id": membership.member_id,
                    "plan_id": membership.plan_id,
                    "amount": amount,
                    "payment_date": date.today(),
                    "payment_mode": membership.payment_mode
                }
            )

            # engine.begin() commits both inserts when the block succeeds.

        return {
            "message": "Membership registered successfully.",
            "membership": {
                "membership_id": membership_id,
                "member_id": membership.member_id,
                "plan_id": membership.plan_id,
                "start_date": start_date,
                "end_date": end_date,
                "membership_status": "Active"
            },
            "payment": {
                "payment_id": payment_id,
                "amount": amount,
                "payment_date": date.today(),
                "payment_mode": membership.payment_mode
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Membership registration failed: {str(e)}"
        )