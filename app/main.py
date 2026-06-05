from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import engine, Base
from .api import api_router


# Try to automatically create all PostgreSQL database tables on startup.
# In production, migrations (e.g. Alembic) are preferred, but this is perfect for the POC.
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")
except Exception as e:
    print(f"Error creating database tables (is Postgres running and DATABASE_URL correct?): {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set CORS origins. Allow all origins for the local POC to make it 100% accessible to web and mobile.
origins = []
if settings.BACKEND_CORS_ORIGINS:
    origins = settings.BACKEND_CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in origins or not origins else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/status")
def get_status():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "database": "postgresql"
    }
