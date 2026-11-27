from fastapi import FastAPI

from app.db import Base, engine
from app.routers import auth, doses, elders, medicines

Base.metadata.create_all(bind=engine)  # no migrations yet

app = FastAPI(title="Elderly Care & Medicine Reminder")
app.include_router(auth.router)
app.include_router(elders.router)
app.include_router(medicines.router)
app.include_router(doses.router)
