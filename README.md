# IRONCORE

Backend API for the IRONCORE Gym Management System.

## Local Database Setup

1. Install and run MySQL locally.
2. Create a database named `gym_db`.
3. Import the existing database dump from [`database/gym_db.sql`](database/gym_db.sql).
4. From the `backend` directory, copy `.env.example` to `.env`.
5. Edit `.env` and enter your own MySQL credentials.
6. From the `backend` directory, install the backend dependencies:

   ```text
   pip install -r requirements.txt
   ```

7. From the `backend` directory, start the backend:

   ```text
   uvicorn main:app --reload
   ```

The backend uses MySQL through SQLAlchemy and PyMySQL. The `.env` file is local-only and must not be committed.
