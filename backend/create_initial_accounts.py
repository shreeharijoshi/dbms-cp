import re

from sqlalchemy import text

from database.connection import engine
from routers.auth import password_hash


ID_PATTERN = re.compile(r"^[A-Za-z]+(?P<numeric_part>\d+)$")


def initial_password(identifier: str) -> str:
    match = ID_PATTERN.fullmatch(identifier)

    if match is None:
        raise ValueError(f"Identifier does not contain a numeric suffix: {identifier}")

    return match.group("numeric_part")


def create_initial_accounts() -> tuple[int, int]:
    created_count = 0
    skipped_count = 0

    with engine.begin() as connection:
        member_records = connection.execute(
            text("""
                SELECT member_id
                FROM members
            """)
        ).mappings().all()

        trainer_records = connection.execute(
            text("""
                SELECT employee_id
                FROM gym_trainers
            """)
        ).mappings().all()

        management_records = connection.execute(
            text("""
                SELECT employee_id
                FROM miscellaneous_employees
                WHERE role = 'Receptionist'
            """)
        ).mappings().all()

        existing_usernames = {
            account["username"]
            for account in connection.execute(
                text("""
                    SELECT username
                    FROM user_accounts
                    FOR UPDATE
                """)
            ).mappings()
        }

        account_records = [
            {
                "username": member["member_id"],
                "password_hash": password_hash.hash(
                    initial_password(member["member_id"])
                ),
                "role": "Member",
                "member_id": member["member_id"],
                "trainer_id": None,
                "management_employee_id": None
            }
            for member in member_records
        ]
        account_records.extend(
            {
                "username": trainer["employee_id"],
                "password_hash": password_hash.hash(
                    initial_password(trainer["employee_id"])
                ),
                "role": "Trainer",
                "member_id": None,
                "trainer_id": trainer["employee_id"],
                "management_employee_id": None
            }
            for trainer in trainer_records
        )
        account_records.extend(
            {
                "username": employee["employee_id"],
                "password_hash": password_hash.hash(
                    initial_password(employee["employee_id"])
                ),
                "role": "Management",
                "member_id": None,
                "trainer_id": None,
                "management_employee_id": employee["employee_id"]
            }
            for employee in management_records
        )

        for account in account_records:
            if account["username"] in existing_usernames:
                skipped_count += 1
                continue

            connection.execute(
                text("""
                    INSERT INTO user_accounts (
                        username,
                        password_hash,
                        role,
                        member_id,
                        trainer_id,
                        management_employee_id,
                        is_active,
                        must_change_password,
                        last_login
                    )
                    VALUES (
                        :username,
                        :password_hash,
                        :role,
                        :member_id,
                        :trainer_id,
                        :management_employee_id,
                        TRUE,
                        TRUE,
                        NULL
                    )
                """),
                account
            )
            existing_usernames.add(account["username"])
            created_count += 1

    return created_count, skipped_count


if __name__ == "__main__":
    created, skipped = create_initial_accounts()
    print(f"Accounts created: {created}")
    print(f"Accounts skipped: {skipped}")
