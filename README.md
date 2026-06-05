# Sports Cricket Tournament Platform Backend

Python FastAPI Backend for the Sports Cricket Tournament platform, serving both React web and Flutter mobile applications.

## Prerequisites
- Python 3.9+
- PostgreSQL database running locally or remotely

## Setup Instructions

1. **Virtual Environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Database**:
   Update `DATABASE_URL` in the `.env` file to match your PostgreSQL instance connection string:
   ```env
   DATABASE_URL="postgresql://<username>:<password>@<host>:<port>/<database>"
   ```

4. **Seed Initial Database Tables & Accounts**:
   ```bash
   python seed.py
   ```
   This command creates all tables in PostgreSQL and registers:
   - **Super Admin**: `superadmin@sports.com` (pw: `password123`)
   - **Department Admin**: `deptadmin@sports.com` (pw: `password123`)
   - **Federation Admin**: `fedadmin@sports.com` (pw: `password123`)
   - **Demo Player, Coach, Sponsor, Scorer** accounts (all with pw: `password123`)

5. **Start Dev Server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   The interactive Swagger UI API documentation will be available at:
   - `http://localhost:8000/docs`
