from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from database.connection import engine
from schemas.membership_plans import MembershipPlanCreate, MembershipPlanUpdate


router = APIRouter(
    prefix="/membership-plans",
    tags=["Membership Plans"]
)


# GET: Retrieve all membership plans
@router.get("/")
def get_all_membership_plans():

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT * FROM membership_plans ORDER BY plan_id")
            )

            plans = result.mappings().all()

            return [dict(plan) for plan in plans]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# GET: Retrieve a membership plan by ID
@router.get("/{plan_id}")
def get_membership_plan(plan_id: str):

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT *
                    FROM membership_plans
                    WHERE plan_id = :plan_id
                """),
                {"plan_id": plan_id}
            )

            plan = result.mappings().first()

            if plan is None:
                raise HTTPException(
                    status_code=404,
                    detail="Membership plan not found"
                )

            return dict(plan)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# POST: Add a new membership plan
@router.post("/")
def add_membership_plan(plan: MembershipPlanCreate):

    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO membership_plans (
                        plan_id,
                        duration,
                        price,
                        group_discount,
                        seasonal_discount
                    )
                    VALUES (
                        :plan_id,
                        :duration,
                        :price,
                        :group_discount,
                        :seasonal_discount
                    )
                """),
                plan.model_dump()
            )

            result = connection.execute(
                text("""
                    SELECT *
                    FROM membership_plans
                    WHERE plan_id = :plan_id
                """),
                {"plan_id": plan.plan_id}
            )

            new_plan = result.mappings().first()

            return {
                "message": "Membership plan added successfully",
                "membership_plan": dict(new_plan)
            }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# PATCH: Update membership plan details
@router.patch("/{plan_id}")
def update_membership_plan(plan_id: str, plan: MembershipPlanUpdate):

    update_data = plan.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update"
        )

    allowed_fields = {
        "duration",
        "price",
        "group_discount",
        "seasonal_discount"
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
                    SELECT plan_id
                    FROM membership_plans
                    WHERE plan_id = :plan_id
                """),
                {"plan_id": plan_id}
            )

            if result.first() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Membership plan not found"
                )

            set_clause = ", ".join(
                f"{field} = :{field}"
                for field in update_data
            )

            update_data["where_plan_id"] = plan_id

            connection.execute(
                text(f"""
                    UPDATE membership_plans
                    SET {set_clause}
                    WHERE plan_id = :where_plan_id
                """),
                update_data
            )

            updated_plan_id = update_data.get("plan_id", plan_id)
            result = connection.execute(
                text("""
                    SELECT *
                    FROM membership_plans
                    WHERE plan_id = :plan_id
                """),
                {"plan_id": updated_plan_id}
            )

            updated_plan = result.mappings().first()

            return {
                "message": "Membership plan updated successfully",
                "membership_plan": dict(updated_plan)
            }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
