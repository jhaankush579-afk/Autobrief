from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, init_db
from models import UserPreferences, ClassSchedule
from briefing import BriefingEngine
from scheduler import scheduler


# ── Pydantic schemas ───────────────────────────────────────────────────

class PreferencesSchema(BaseModel):
    city: str = "London"
    news_topics: str = "technology"
    telegram_chat_id: str = ""


class PreferencesOut(PreferencesSchema):
    id: int
    model_config = {"from_attributes": True}


class ScheduleSchema(BaseModel):
    day_of_week: str
    time: str
    subject: str
    location: str = ""


class ScheduleOut(ScheduleSchema):
    id: int
    model_config = {"from_attributes": True}


# ── App lifecycle ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.start()
    print("[AutoBrief] Scheduler started.")
    yield
    scheduler.shutdown(wait=False)
    print("[AutoBrief] Scheduler stopped.")


app = FastAPI(title="AutoBrief API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Preferences CRUD ──────────────────────────────────────────────────

@app.get("/api/preferences", response_model=Optional[PreferencesOut])
def get_preferences(db: Session = Depends(get_db)):
    return db.query(UserPreferences).first()


@app.post("/api/preferences", response_model=PreferencesOut)
def save_preferences(data: PreferencesSchema, db: Session = Depends(get_db)):
    prefs = db.query(UserPreferences).first()
    if prefs:
        prefs.city = data.city
        prefs.news_topics = data.news_topics
        prefs.telegram_chat_id = data.telegram_chat_id
    else:
        prefs = UserPreferences(
            city=data.city,
            news_topics=data.news_topics,
            telegram_chat_id=data.telegram_chat_id,
        )
        db.add(prefs)
    db.commit()
    db.refresh(prefs)
    return prefs


# ── Schedule CRUD ──────────────────────────────────────────────────────

@app.get("/api/schedule", response_model=list[ScheduleOut])
def list_schedule(day: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ClassSchedule)
    if day:
        query = query.filter(ClassSchedule.day_of_week == day)
    return query.order_by(ClassSchedule.day_of_week, ClassSchedule.time).all()


@app.post("/api/schedule", response_model=ScheduleOut)
def create_schedule(data: ScheduleSchema, db: Session = Depends(get_db)):
    entry = ClassSchedule(
        day_of_week=data.day_of_week,
        time=data.time,
        subject=data.subject,
        location=data.location,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@app.put("/api/schedule/{entry_id}", response_model=ScheduleOut)
def update_schedule(
    entry_id: int, data: ScheduleSchema, db: Session = Depends(get_db)
):
    entry = db.query(ClassSchedule).filter(ClassSchedule.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Schedule entry not found.")
    entry.day_of_week = data.day_of_week
    entry.time = data.time
    entry.subject = data.subject
    entry.location = data.location
    db.commit()
    db.refresh(entry)
    return entry


@app.delete("/api/schedule/{entry_id}")
def delete_schedule(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(ClassSchedule).filter(ClassSchedule.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Schedule entry not found.")
    db.delete(entry)
    db.commit()
    return {"ok": True}


# ── Trigger briefing ──────────────────────────────────────────────────

@app.post("/api/trigger")
async def trigger_briefing():
    engine = BriefingEngine()
    result = await engine.run()
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("detail", "Unknown error"))
    return result


@app.post("/api/preview")
async def preview_briefing():
    engine = BriefingEngine()
    result = await engine.run(preview_only=True)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("detail", "Unknown error"))
    return result
