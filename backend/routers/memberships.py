import logging
from contextlib import contextmanager
from datetime import date, timedelta
from calendar import monthrange
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from database.connection import engine
from dependencies.auth import require_roles
from schemas.memberships import MembershipCreate, MembershipRenewal


logger = logging.getLogger(__name__)

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


MEMBER_ID_PATTERN = re.compile(r"^MEM1\d{4}\d{2}$")


def generate_membership_id(member_id: str) -> str:
    if not MEMBER_ID_PATTERN.fullmatch(member_id):
        raise HTTPException(
            status_code=400,
            detail="Member ID does not match the required format."
        )

    return f"MSH{member_id[3:]}"


@contextmanager
def generate_payment_id(connection, payment_date: date):
    date_part = payment_date.strftime("%y%m%d")
    lock_name = f"ironcore_payment_id_{date_part}"
    lock_acquired = False

    try:
        lock_result = connection.execute(
            text("SELECT GET_LOCK(:lock_name, 10)"),
            {"lock_name": lock_name}
        ).scalar()

        if lock_result != 1:
            raise HTTPException(
                status_code=503,
                detail="Could not reserve a payment ID. Please try again."
            )

        lock_acquired = True
        payment_id_prefix = f"PAY{date_part}"
        latest_payment_id = connection.execute(
            text("""
                SELECT payment_id
                FROM payments
                WHERE payment_id REGEXP :payment_id_pattern
                ORDER BY payment_id DESC
                LIMIT 1
                FOR UPDATE
            """),
            {
                "payment_id_pattern": f"^PAY{date_part}[0-9]{{2}}$"
            }
        ).scalar()
        next_sequence = (
            int(latest_payment_id[-2:]) + 1
            if latest_payment_id is not None
            else 1
        )

        if next_sequence > 99:
            raise HTTPException(
                status_code=409,
                detail="The daily payment ID limit has been reached."
            )

        yield f"{payment_id_prefix}{next_sequence:02d}"

    finally:
        if lock_acquired:
            connection.execute(
                text("SELECT RELEASE_LOCK(:lock_name)"),
                {"lock_name": lock_name}
            )


@router.post(
    "/renew/{membership_id}",
    dependencies=[Depends(require_roles("Management"))]
)
def renew_membership(membership_id: str, renewal: MembershipRenewal):
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            current_membership = connection.execute(
                text("""
                    SELECT membership_id, member_id, membership_status, end_date
                    FROM members_plans
                    WHERE membership_id = :membership_id
                    FOR UPDATE
                """),
                {"membership_id": membership_id}
            ).mappings().first()

            if current_membership is None:
                raise HTTPException(
                    status_code=404,
                    detail="Membership not found."
                )

            plan = connection.execute(
                text("""
                    SELECT duration, price
                    FROM membership_plans
                    WHERE plan_id = :plan_id
                """),
                {"plan_id": renewal.plan_id}
            ).mappings().first()

            if plan is None:
                raise HTTPException(
                    status_code=404,
                    detail="Membership plan not found."
                )

            member = connection.execute(
                text("""
                    SELECT member_status
                    FROM members
                    WHERE member_id = :member_id
                    FOR UPDATE
                """),
                {"member_id": current_membership["member_id"]}
            ).mappings().first()

            if member is None:
                raise HTTPException(
                    status_code=404,
                    detail="Member not found."
                )

            if member["member_status"] != "Active":
                raise HTTPException(
                    status_code=400,
                    detail="Inactive members cannot renew a membership."
                )

            today = date.today()
            previous_payment = connection.execute(
                text("""
                    SELECT payment_id
                    FROM payments
                    WHERE membership_id = :membership_id
                      AND payment_date = :payment_date
                    LIMIT 1
                """),
                {
                    "membership_id": membership_id,
                    "payment_date": today
                }
            ).first()

            if previous_payment is not None:
                raise HTTPException(
                    status_code=409,
                    detail="A renewal for this membership was already processed today."
                )

            current_end_date = current_membership["end_date"]

            if (
                current_membership["membership_status"] == "Active"
                and current_end_date is not None
                and current_end_date >= today
            ):
                start_date = current_end_date + timedelta(days=1)
            else:
                start_date = today

            end_date = calculate_end_date(
                start_date,
                plan["duration"]
            )

            connection.execute(
                text("""
                    UPDATE members_plans
                    SET plan_id = :plan_id,
                        start_date = :start_date,
                        end_date = :end_date,
                        membership_status = 'Active'
                    WHERE membership_id = :membership_id
                """),
                {
                    "membership_id": membership_id,
                    "plan_id": renewal.plan_id,
                    "start_date": start_date,
                    "end_date": end_date
                }
            )

            with generate_payment_id(connection, today) as payment_id:
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
                        "member_id": current_membership["member_id"],
                        "plan_id": renewal.plan_id,
                        "amount": plan["price"],
                        "payment_date": today,
                        "payment_mode": renewal.payment_mode
                    }
                )

                transaction.commit()

            return {
                "message": "Membership renewed successfully.",
                "membership": {
                    "membership_id": membership_id,
                    "member_id": current_membership["member_id"],
                    "plan_id": renewal.plan_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "membership_status": "Active"
                },
                "payment": {
                    "payment_id": payment_id,
                    "amount": plan["price"],
                    "payment_date": today,
                    "payment_mode": renewal.payment_mode
                }
            }

        except HTTPException:
            if transaction.is_active:
                transaction.rollback()
            raise

        except Exception:
            if transaction.is_active:
                transaction.rollback()
            logger.exception("Unexpected membership renewal error.")
            raise HTTPException(
                status_code=500,
                detail="Internal server error."
            )


@router.post("/", dependencies=[Depends(require_roles("Management"))])
def register_membership(membership: MembershipCreate):
    with engine.connect() as connection:
        transaction = connection.begin()
        try:

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

            membership_id = generate_membership_id(membership.member_id)

            existing_membership = connection.execute(
                text("""
                    SELECT membership_id
                    FROM members_plans
                    WHERE membership_id = :membership_id
                    FOR UPDATE
                """),
                {"membership_id": membership_id}
            ).first()

            if existing_membership:
                raise HTTPException(
                    status_code=400,
                    detail="Membership already exists. Use renewal."
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
            payment_date = date.today()
            with generate_payment_id(
                connection,
                payment_date
            ) as payment_id:
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
                        "payment_date": payment_date,
                        "payment_mode": membership.payment_mode
                    }
                )

                transaction.commit()

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
                    "payment_date": payment_date,
                    "payment_mode": membership.payment_mode
                }
            }

        except HTTPException:
            if transaction.is_active:
                transaction.rollback()
            raise

        except Exception:
            if transaction.is_active:
                transaction.rollback()
            logger.exception("Unexpected membership registration error.")
            raise HTTPException(
                status_code=500,
                detail="Internal server error."
            )