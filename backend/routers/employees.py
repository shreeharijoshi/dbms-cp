import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from database.connection import engine
from dependencies.auth import require_roles
from schemas.employees import EmployeeCreate, EmployeeUpdate


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/employees",
    tags=["Employees"]
)


@router.get("/")
def get_all_employees():
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT *
                    FROM miscellaneous_employees
                    ORDER BY employee_id
                """)
            )

            employees = result.mappings().all()

            return [dict(employee) for employee in employees]

    except Exception:
        logger.exception("Unexpected error in employees endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )


@router.get("/{employee_id}")
def get_employee(employee_id: str):
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT *
                    FROM miscellaneous_employees
                    WHERE employee_id = :employee_id
                """),
                {"employee_id": employee_id}
            )

            employee = result.mappings().first()

            if employee is None:
                raise HTTPException(
                    status_code=404,
                    detail="Employee not found"
                )

            return dict(employee)

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in employees endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )


@router.post("/", dependencies=[Depends(require_roles("Management"))])
def add_employee(employee: EmployeeCreate):
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO miscellaneous_employees (
                        employee_id,
                        employee_name,
                        role
                    )
                    VALUES (
                        :employee_id,
                        :employee_name,
                        :role
                    )
                """),
                employee.model_dump()
            )

            result = connection.execute(
                text("""
                    SELECT *
                    FROM miscellaneous_employees
                    WHERE employee_id = :employee_id
                """),
                {"employee_id": employee.employee_id}
            )

            new_employee = result.mappings().first()

            return {
                "message": "Employee added successfully",
                "employee": dict(new_employee)
            }

    except Exception:
        logger.exception("Unexpected error in employees endpoint.")
        raise HTTPException(
            status_code=400,
            detail="Request could not be completed."
        )


@router.patch(
    "/{employee_id}",
    dependencies=[Depends(require_roles("Management"))]
)
def update_employee(employee_id: str, employee: EmployeeUpdate):
    update_data = employee.model_dump(exclude_unset=True)

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
                    FROM miscellaneous_employees
                    WHERE employee_id = :employee_id
                """),
                {"employee_id": employee_id}
            )

            if result.first() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Employee not found"
                )

            set_clause = ", ".join(
                f"{field} = :{field}"
                for field in update_data
            )

            update_data["employee_id"] = employee_id

            connection.execute(
                text(f"""
                    UPDATE miscellaneous_employees
                    SET {set_clause}
                    WHERE employee_id = :employee_id
                """),
                update_data
            )

            result = connection.execute(
                text("""
                    SELECT *
                    FROM miscellaneous_employees
                    WHERE employee_id = :employee_id
                """),
                {"employee_id": employee_id}
            )

            updated_employee = result.mappings().first()

            return {
                "message": "Employee updated successfully",
                "employee": dict(updated_employee)
            }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in employees endpoint.")
        raise HTTPException(
            status_code=400,
            detail="Request could not be completed."
        )


@router.delete(
    "/{employee_id}",
    dependencies=[Depends(require_roles("Management"))]
)
def delete_employee(employee_id: str):
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    SELECT employee_id
                    FROM miscellaneous_employees
                    WHERE employee_id = :employee_id
                """),
                {"employee_id": employee_id}
            )

            if result.first() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Employee not found"
                )

            connection.execute(
                text("""
                    DELETE FROM miscellaneous_employees
                    WHERE employee_id = :employee_id
                """),
                {"employee_id": employee_id}
            )

            return {
                "message": "Employee deleted successfully",
                "employee_id": employee_id
            }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in employees endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )
