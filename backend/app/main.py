# 1.1.0 main.py

from fastapi import FastAPI, Depends
from .db import init_db, SessionLocal
from sqlalchemy.orm import Session

app = FastAPI(title="SMS Viewer API")

@app.on_event("startup")
def on_startup():
    init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def health_check():
    return {"status": "OK", "message": "SMS Viewer is running."}
