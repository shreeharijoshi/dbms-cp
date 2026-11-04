import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from database.connection import engine
from dependencies.auth import require_roles
from schemas.trainers import TrainerCreate, TrainerUpdate


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/trainers",
    tags=["Trainers"]
)


@router.get("/")
def get_all_trainers():
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT * FROM gym_trainers ORDER BY employee_id")
            )

            trainers = result.mappings().all()

            return [dict(trainer) for trainer in trainers]

    except Exception:
        logger.exception("Unexpected error in trainers endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )


@router.get("/{employee_id}")
def get_trainer(employee_id: str):
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT *
                    FROM gym_trainers
                    WHERE employee_id = :employee_id
                """),
                {"employee_id": employee_id}
            )

            trainer = result.mappings().first()

            if trainer is None:
                raise HTTPException(
                    status_code=404,
                    detail="Trainer not found"
                )

            return dict(trainer)

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in trainers endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )


@router.post("/", dependencies=[Depends(require_roles("Management"))])
def add_trainer(trainer: TrainerCreate):
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO gym_trainers (
                        employee_id,
                        trainer_name,
                        dob,
                        gender,
                        height,
                        weight,
                        speciality,
                        qualification,
                        shift
                    )
                    VALUES (
                        :employee_id,
                        :trainer_name,
                        :dob,
                        :gender,
                        :height,
                        :weight,
                        :speciality,
                        :qualification,
                        :shift
                    )
                """),
                trainer.model_dump()
            )

            result = connection.execute(
                text("""
                    SELECT *
                    FROM gym_trainers
                    WHERE employee_id = :employee_id
                """),
                {"employee_id": trainer.employee_id}
            )

            new_trainer = result.mappings().first()

            return {
                "message": "Trainer added successfully",
                "trainer": dict(new_trainer)
            }

    except Exception:
        logger.exception("Unexpected error in trainers endpoint.")
        raise HTTPException(
            status_code=400,
            detail="Request could not be completed."
        )


@router.patch(
    "/{employee_id}",
    dependencies=[Depends(require_roles("Management"))]
)
def update_trainer(employee_id: str, trainer: TrainerUpdate):
    update_data = trainer.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update"
        )

    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    SELECT employee_id
                    FROM gym_trainers
                    WHERE employee_id = :employee_id
                """),
                {"employee_id": employee_id}
            )

            if result.first() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Trainer not found"
                )

            set_clause = ", ".join(
                f"{field} = :{field}"
                for field in update_data
            )

            update_data["employee_id"] = employee_id

            connection.execute(
                text(f"""
                    UPDATE gym_trainers
                    SET {set_clause}
                    WHERE employee_id = :employee_id
                """),
                update_data
            )

            result = connection.execute(
                text("""
                    SELECT *
                    FROM gym_trainers
                    WHERE employee_id = :employee_id
                """),
                {"employee_id": employee_id}
            )

            updated_trainer = result.mappings().first()

            return {
                "message": "Trainer updated successfully",
                "trainer": dict(updated_trainer)
            }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in trainers endpoint.")
        raise HTTPException(
            status_code=400,
            detail="Request could not be completed."
        )


@router.delete(
    "/{employee_id}",
    dependencies=[Depends(require_roles("Management"))]
)
def delete_trainer(employee_id: str):
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    SELECT employee_id
                    FROM gym_trainers
                    WHERE employee_id = :employee_id
                """),
                {"employee_id": employee_id}
            )

            if result.first() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Trainer not found"
                )

            connection.execute(
                text("""
                    DELETE FROM gym_trainers
                    WHERE employee_id = :employee_id
                """),
                {"employee_id": employee_id}
            )

            return {
                "message": "Trainer deleted successfully",
                "employee_id": employee_id
            }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in trainers endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )
