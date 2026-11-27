from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import Base, engine
from app.routers import appointments, auth, doses, elders, medicines, screen
from app.scheduler import start_scheduler

Base.metadata.create_all(bind=engine)  # no migrations yet


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = start_scheduler() if settings.run_scheduler else None
    yield
    if scheduler:
        scheduler.shutdown()


app = FastAPI(title="Elderly Care & Medicine Reminder", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(elders.router)
app.include_router(medicines.router)
app.include_router(doses.router)
app.include_router(appointments.router)
app.include_router(screen.router)
