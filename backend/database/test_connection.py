from connection import engine
from sqlalchemy import text

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT DATABASE()"))
        database_name = result.scalar()

        print("CONNECTION SUCCESSFUL!")
        print("Connected database:", database_name)

except Exception as e:
    print("CONNECTION FAILED!")
    print("Error:", e)