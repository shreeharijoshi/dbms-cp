import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from database.connection import engine
from routers import auth, employees, expenses, inventory, members, membership_plans, memberships, payments, trainers

logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
templates = Jinja2Templates(directory=str(FRONTEND_DIR / "templates"))

app = FastAPI(
    title="IRONCORE Gym Management System",
    description="Backend API for the IRONCORE Gym Management Application",
    version="1.0.0"
)

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR / "static")),
    name="static"
)

app.include_router(members.router)
app.include_router(membership_plans.router)
app.include_router(memberships.router)
app.include_router(trainers.router)
app.include_router(inventory.router)
app.include_router(employees.router)
app.include_router(expenses.router)
app.include_router(payments.router)
app.include_router(auth.router)


@app.get("/", name="home_page")
@app.get("/members", name="members_page")
def members_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="members.html"
    )


@app.get("/membership-plans", name="membership_plans_page")
def membership_plans_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="membership_plans.html"
    )


@app.get("/memberships", name="memberships_page")
def memberships_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="memberships.html"
    )


@app.get("/api/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "Healthy",
            "database": "Connected"
        }

    except Exception:
        logger.exception("Database health check failed.")
        return {
            "status": "Unhealthy",
            "database": "Disconnected"
        }
