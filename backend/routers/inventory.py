import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from database.connection import engine
from dependencies.auth import require_roles
from schemas.inventory import InventoryCreate, InventoryUpdate


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"]
)


@router.get("/")
def get_all_inventory():
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT * FROM inventory ORDER BY inventory_id")
            )

            inventory_records = result.mappings().all()

            return [dict(record) for record in inventory_records]

    except Exception:
        logger.exception("Unexpected error in inventory endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )


@router.get("/{inventory_id}")
def get_inventory(inventory_id: str):
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT *
                    FROM inventory
                    WHERE inventory_id = :inventory_id
                """),
                {"inventory_id": inventory_id}
            )

            inventory_record = result.mappings().first()

            if inventory_record is None:
                raise HTTPException(
                    status_code=404,
                    detail="Inventory record not found"
                )

            return dict(inventory_record)

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in inventory endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )


@router.post("/", dependencies=[Depends(require_roles("Management"))])
def add_inventory(inventory: InventoryCreate):
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO inventory (
                        inventory_id,
                        item_name,
                        category,
                        quantity,
                        cost,
                        purchase_date,
                        inventory_status
                    )
                    VALUES (
                        :inventory_id,
                        :item_name,
                        :category,
                        :quantity,
                        :cost,
                        :purchase_date,
                        :inventory_status
                    )
                """),
                inventory.model_dump()
            )

            result = connection.execute(
                text("""
                    SELECT *
                    FROM inventory
                    WHERE inventory_id = :inventory_id
                """),
                {"inventory_id": inventory.inventory_id}
            )

            new_inventory = result.mappings().first()

            return {
                "message": "Inventory record added successfully",
                "inventory": dict(new_inventory)
            }

    except Exception:
        logger.exception("Unexpected error in inventory endpoint.")
        raise HTTPException(
            status_code=400,
            detail="Request could not be completed."
        )


@router.patch(
    "/{inventory_id}",
    dependencies=[Depends(require_roles("Management"))]
)
def update_inventory(inventory_id: str, inventory: InventoryUpdate):
    update_data = inventory.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update"
        )

    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    SELECT inventory_id
                    FROM inventory
                    WHERE inventory_id = :inventory_id
                """),
                {"inventory_id": inventory_id}
            )

            if result.first() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Inventory record not found"
                )

            set_clause = ", ".join(
                f"{field} = :{field}"
                for field in update_data
            )

            update_data["inventory_id"] = inventory_id

            connection.execute(
                text(f"""
                    UPDATE inventory
                    SET {set_clause}
                    WHERE inventory_id = :inventory_id
                """),
                update_data
            )

            result = connection.execute(
                text("""
                    SELECT *
                    FROM inventory
                    WHERE inventory_id = :inventory_id
                """),
                {"inventory_id": inventory_id}
            )

            updated_inventory = result.mappings().first()

            return {
                "message": "Inventory record updated successfully",
                "inventory": dict(updated_inventory)
            }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in inventory endpoint.")
        raise HTTPException(
            status_code=400,
            detail="Request could not be completed."
        )


@router.delete(
    "/{inventory_id}",
    dependencies=[Depends(require_roles("Management"))]
)
def delete_inventory(inventory_id: str):
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    SELECT inventory_id
                    FROM inventory
                    WHERE inventory_id = :inventory_id
                """),
                {"inventory_id": inventory_id}
            )

            if result.first() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Inventory record not found"
                )

            connection.execute(
                text("""
                    DELETE FROM inventory
                    WHERE inventory_id = :inventory_id
                """),
                {"inventory_id": inventory_id}
            )

            return {
                "message": "Inventory record deleted successfully",
                "inventory_id": inventory_id
            }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error in inventory endpoint.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )
