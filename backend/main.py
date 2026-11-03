from fastapi import FastAPI
from sqlalchemy import text
from database.connection import engine
from routers import members, membership_plans, memberships

app = FastAPI(
    title="IRONCORE Gym Management System",
    description="Backend API for the IRONCORE Gym Management Application",
    version="1.0.0"
)

app.include_router(members.router)
app.include_router(membership_plans.router)
app.include_router(memberships.router)


@app.get("/")
def home():
    return {
        "message": "Welcome to IRONCORE Gym Management System",
        "status": "Running"
    }


@app.get("/api/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "Healthy",
            "database": "Connected"
        }

    except Exception as e:
        return {
            "status": "Unhealthy",
            "database": "Disconnected",
            "error": str(e)
        }