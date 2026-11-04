import logging
from fastapi import APIRouter, HTTPException
from fastapi import Depends
from sqlalchemy import text
from database.connection import engine
from dependencies.auth import require_roles
from schemas.members import MemberCreate, MemberUpdate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/members",
    tags=["Members"]
)


# GET: Retrieve all members
@router.get("/")
def get_all_members():

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT * FROM members ORDER BY member_id")
            )

            members = result.mappings().all()

            return [dict(member) for member in members]

    except Exception:
        logger.exception("Unexpected error in members endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )


# GET: Retrieve a member by ID
@router.get("/{member_id}")
def get_member(member_id: str):

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT *
                    FROM members
                    WHERE member_id = :member_id
                """),
                {"member_id": member_id}
            )

            member = result.mappings().first()

            if member is None:
                raise HTTPException(
                    status_code=404,
                    detail="Member not found"
                )

            return dict(member)

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in members endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )

# POST: Add a new member
@router.post("/", dependencies=[Depends(require_roles("Management"))])
def add_member(member: MemberCreate):

    try:
        with engine.begin() as connection:

            connection.execute(
                text("""
                    INSERT INTO members (
                        member_id,
                        member_name,
                        gender,
                        height,
                        weight,
                        contact,
                        dob,
                        PT
                    )
                    VALUES (
                        :member_id,
                        :member_name,
                        :gender,
                        :height,
                        :weight,
                        :contact,
                        :dob,
                        :PT
                    )
                """),
                member.model_dump()
            )

            result = connection.execute(
                text("""
                    SELECT *
                    FROM members
                    WHERE member_id = :member_id
                """),
                {"member_id": member.member_id}
            )

            new_member = result.mappings().first()

            return {
                "message": "Member added successfully",
                "member": dict(new_member)
            }

    except Exception:
        logger.exception("Unexpected error in members endpoint.")
        raise HTTPException(
            status_code=400,
            detail="Request could not be completed."
        )

# PATCH: Update member details
@router.patch("/{member_id}", dependencies=[Depends(require_roles("Management"))])
def update_member(member_id: str, member: MemberUpdate):

    update_data = member.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update"
        )

    allowed_fields = {
        "member_name",
        "gender",
        "height",
        "weight",
        "contact",
        "dob",
        "PT"
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
                    SELECT member_id
                    FROM members
                    WHERE member_id = :member_id
                """),
                {"member_id": member_id}
            )

            if result.first() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Member not found"
                )

            set_clause = ", ".join(
                f"{field} = :{field}"
                for field in update_data
            )

            update_data["member_id"] = member_id

            connection.execute(
                text(f"""
                    UPDATE members
                    SET {set_clause}
                    WHERE member_id = :member_id
                """),
                update_data
            )

            result = connection.execute(
                text("""
                    SELECT *
                    FROM members
                    WHERE member_id = :member_id
                """),
                {"member_id": member_id}
            )

            updated_member = result.mappings().first()

            return {
                "message": "Member updated successfully",
                "member": dict(updated_member)
            }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in members endpoint.")
        raise HTTPException(
            status_code=400,
            detail="Request could not be completed."
        )

# PATCH: Deactivate a member
@router.patch(
    "/{member_id}/deactivate",
    dependencies=[Depends(require_roles("Management"))]
)
def deactivate_member(member_id: str):

    try:
        with engine.begin() as connection:

            result = connection.execute(
                text("""
                    UPDATE members
                    SET member_status = 'Inactive'
                    WHERE member_id = :member_id
                    AND member_status = 'Active'
                """),
                {"member_id": member_id}
            )

            if result.rowcount == 0:
                check = connection.execute(
                    text("""
                        SELECT member_status
                        FROM members
                        WHERE member_id = :member_id
                    """),
                    {"member_id": member_id}
                ).first()

                if check is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Member not found"
                    )

                raise HTTPException(
                    status_code=400,
                    detail="Member is already inactive"
                )

            return {
                "message": "Member deactivated successfully",
                "member_id": member_id,
                "member_status": "Inactive"
            }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in members endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )