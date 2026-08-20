import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import job, user  # noqa: F401 — register models
from app.routers import admin, auth, jobs
from app.services.ingestion import fetch_and_store_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def scheduled_fetch():
    db = SessionLocal()
    try:
        await fetch_and_store_all(db)
    except Exception as e:
        logger.error("Scheduled fetch failed: %s", e)
    finally:
        db.close()


def run_migrations():
    """Add new columns / tables to existing SQLite DB."""
    from app.models.user import AlertLog, FavoriteJob, User, UserPreferences, UserProfile

    for model in (User, UserPreferences, UserProfile, FavoriteJob, AlertLog):
        model.__table__.create(bind=engine, checkfirst=True)

    cols = [
        ("full_content", "TEXT"),
        ("notification_url", "VARCHAR(1000)"),
        ("age_limit", "VARCHAR(200)"),
        ("application_fee", "VARCHAR(200)"),
        ("sections_json", "TEXT"),
    ]
    with engine.connect() as conn:
        for name, typ in cols:
            try:
                conn.execute(text(f"ALTER TABLE jobs ADD COLUMN {name} {typ}"))
                conn.commit()
            except Exception:
                pass
        for idx_sql in (
            "CREATE INDEX IF NOT EXISTS ix_jobs_published_date ON jobs (published_date)",
            "CREATE INDEX IF NOT EXISTS ix_jobs_active_category_lastdate ON jobs (is_active, category, last_date)",
        ):
            try:
                conn.execute(text(idx_sql))
                conn.commit()
            except Exception:
                pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("data").mkdir(exist_ok=True)
    Base.metadata.create_all(bind=engine)
    run_migrations()

    if settings.skip_initial_fetch:
        logger.info("Skipping initial fetch (SKIP_INITIAL_FETCH=1)")
    else:
        async def _initial_fetch():
            # Let /health pass before scraping dozens of portals (avoids OOM/unhealthy on small VPS).
            await asyncio.sleep(30)
            db = SessionLocal()
            try:
                await fetch_and_store_all(db)
            except Exception as e:
                logger.warning("Initial fetch failed: %s", e)
            finally:
                db.close()

        asyncio.create_task(_initial_fetch())

    scheduler.add_job(
        scheduled_fetch,
        "interval",
        minutes=settings.fetch_interval_minutes,
        id="job_fetch",
    )
    scheduler.start()
    logger.info("IndiaJob API started - fetching every %d minutes", settings.fetch_interval_minutes)

    yield

    scheduler.shutdown()


app = FastAPI(
    title="IndiaJob API",
    description="Government job notifications aggregator for India",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api", tags=["jobs"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(admin.router, prefix="/api", tags=["admin"])


@app.get("/")
def root():
    return {
        "service": "IndiaJob API",
        "message": "Use the web app at http://localhost:3000 (frontend). This port is API-only.",
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
