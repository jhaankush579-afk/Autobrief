"""Comprehensive tests for the AutoBrief backend.

Covers: database models, CRUD API endpoints, BriefingEngine (weather, news,
message builder), and the preview/trigger endpoints.
"""

import os
import sys
import asyncio

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend package is importable
sys.path.insert(0, os.path.dirname(__file__))

from database import Base, get_db
from models import UserPreferences, ClassSchedule
from briefing import BriefingEngine, DAYS

# ── Test DB setup ──────────────────────────────────────────────────────

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """Create fresh tables for every test, tear down after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client():
    # Lazy import to avoid scheduler side-effects at module level
    from main import app
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ── Model tests ────────────────────────────────────────────────────────

class TestModels:
    def test_create_user_preferences(self):
        db = TestSession()
        prefs = UserPreferences(city="Berlin", news_topics="science", telegram_chat_id="999")
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
        assert prefs.id is not None
        assert prefs.city == "Berlin"
        assert prefs.news_topics == "science"
        assert prefs.telegram_chat_id == "999"
        db.close()

    def test_create_class_schedule(self):
        db = TestSession()
        entry = ClassSchedule(
            day_of_week="Monday", time="09:00", subject="Math", location="Room 101"
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        assert entry.id is not None
        assert entry.day_of_week == "Monday"
        assert entry.subject == "Math"
        assert entry.location == "Room 101"
        db.close()


# ── Preferences API tests ─────────────────────────────────────────────

class TestPreferencesAPI:
    def test_get_preferences_empty(self, client):
        resp = client.get("/api/preferences")
        assert resp.status_code == 200
        assert resp.json() is None

    def test_save_and_get_preferences(self, client):
        payload = {"city": "Tokyo", "news_topics": "tech", "telegram_chat_id": "123"}
        resp = client.post("/api/preferences", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["city"] == "Tokyo"
        assert data["id"] is not None

        resp2 = client.get("/api/preferences")
        assert resp2.json()["city"] == "Tokyo"

    def test_update_preferences(self, client):
        client.post(
            "/api/preferences",
            json={"city": "A", "news_topics": "b", "telegram_chat_id": "1"},
        )
        resp = client.post(
            "/api/preferences",
            json={"city": "B", "news_topics": "c", "telegram_chat_id": "2"},
        )
        assert resp.json()["city"] == "B"
        # Still only one row
        assert resp.json()["id"] == 1


# ── Schedule API tests ─────────────────────────────────────────────────

class TestScheduleAPI:
    def test_list_empty(self, client):
        resp = client.get("/api/schedule")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_and_list(self, client):
        payload = {
            "day_of_week": "Wednesday",
            "time": "14:00",
            "subject": "Physics",
            "location": "Lab 3",
        }
        resp = client.post("/api/schedule", json=payload)
        assert resp.status_code == 200
        assert resp.json()["subject"] == "Physics"

        all_entries = client.get("/api/schedule").json()
        assert len(all_entries) == 1

    def test_filter_by_day(self, client):
        client.post(
            "/api/schedule",
            json={"day_of_week": "Monday", "time": "09:00", "subject": "Math"},
        )
        client.post(
            "/api/schedule",
            json={"day_of_week": "Tuesday", "time": "10:00", "subject": "English"},
        )
        resp = client.get("/api/schedule", params={"day": "Monday"})
        data = resp.json()
        assert len(data) == 1
        assert data[0]["subject"] == "Math"

    def test_update_schedule(self, client):
        resp = client.post(
            "/api/schedule",
            json={"day_of_week": "Monday", "time": "09:00", "subject": "Math"},
        )
        entry_id = resp.json()["id"]
        resp2 = client.put(
            f"/api/schedule/{entry_id}",
            json={"day_of_week": "Monday", "time": "10:00", "subject": "Algebra", "location": "Room 5"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["subject"] == "Algebra"
        assert resp2.json()["time"] == "10:00"

    def test_delete_schedule(self, client):
        resp = client.post(
            "/api/schedule",
            json={"day_of_week": "Friday", "time": "11:00", "subject": "Art"},
        )
        entry_id = resp.json()["id"]
        del_resp = client.delete(f"/api/schedule/{entry_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["ok"] is True

        all_entries = client.get("/api/schedule").json()
        assert len(all_entries) == 0

    def test_delete_nonexistent(self, client):
        resp = client.delete("/api/schedule/9999")
        assert resp.status_code == 404

    def test_update_nonexistent(self, client):
        resp = client.put(
            "/api/schedule/9999",
            json={"day_of_week": "Monday", "time": "09:00", "subject": "X", "location": ""},
        )
        assert resp.status_code == 404


# ── BriefingEngine unit tests ─────────────────────────────────────────

class TestBriefingEngine:
    def test_build_message_with_all_data(self):
        engine = BriefingEngine()
        weather = {
            "city": "London",
            "temp": 15.2,
            "feels_like": 13.0,
            "description": "Partly Cloudy",
            "humidity": 72,
            "wind_speed": 12.5,
        }
        news = [
            {"title": "AI Breakthrough", "source": "TechCrunch", "url": "https://example.com/1"},
            {"title": "Climate Summit", "source": "BBC", "url": "https://example.com/2"},
        ]
        schedule = [
            {"time": "09:00", "subject": "Math", "location": "Room 101"},
            {"time": "11:00", "subject": "Physics", "location": ""},
        ]
        msg = engine.build_message(weather, news, schedule)
        assert "London" in msg
        assert "15.2" in msg
        assert "Partly Cloudy" in msg
        assert "AI Breakthrough" in msg
        assert "Climate Summit" in msg
        assert "Math" in msg
        assert "Room 101" in msg
        assert "Physics" in msg

    def test_build_message_no_data(self):
        engine = BriefingEngine()
        msg = engine.build_message(None, [], [])
        assert "unavailable" in msg
        assert "No headlines" in msg
        assert "No classes" in msg

    def test_build_message_no_humidity(self):
        engine = BriefingEngine()
        weather = {
            "city": "TestCity",
            "temp": 20,
            "feels_like": 20,
            "description": "Clear",
            "humidity": None,
            "wind_speed": 5,
        }
        msg = engine.build_message(weather, [], [])
        assert "Humidity" not in msg
        assert "TestCity" in msg

    @pytest.mark.asyncio
    async def test_fetch_weather_real(self):
        """Integration test: actually hit Open-Meteo (free, no key)."""
        engine = BriefingEngine()
        weather = await engine.fetch_weather("London")
        assert "city" in weather
        assert "temp" in weather
        assert isinstance(weather["temp"], (int, float))
        assert "description" in weather

    @pytest.mark.asyncio
    async def test_fetch_weather_bad_city(self):
        engine = BriefingEngine()
        with pytest.raises(ValueError, match="not found"):
            await engine.fetch_weather("Xyzzyplughville999")

    @pytest.mark.asyncio
    async def test_fetch_news_real(self):
        """Integration test: actually hit Google News RSS (free, no key)."""
        engine = BriefingEngine()
        articles = await engine.fetch_news("technology", count=2)
        assert isinstance(articles, list)
        # Google News should return something for "technology"
        assert len(articles) > 0
        assert "title" in articles[0]
        assert "source" in articles[0]

    @pytest.mark.asyncio
    async def test_run_no_preferences(self):
        """Engine.run should return error when no prefs exist."""
        engine = BriefingEngine()
        # Patch SessionLocal to use test DB
        with patch("briefing.SessionLocal", TestSession):
            result = await engine.run()
        assert result["ok"] is False
        assert "No user preferences" in result["detail"]

    @pytest.mark.asyncio
    async def test_run_preview_mode(self):
        """Engine.run(preview_only=True) should return the message without sending."""
        # Insert preferences into test DB
        db = TestSession()
        db.add(UserPreferences(city="Paris", news_topics="science", telegram_chat_id=""))
        db.commit()
        db.close()

        engine = BriefingEngine()
        with patch("briefing.SessionLocal", TestSession):
            result = await engine.run(preview_only=True)
        assert result["ok"] is True
        assert "message" in result
        assert result["sent"] is False
        # Message should contain the daily briefing header regardless of API availability
        assert "Daily Briefing" in result["message"]


# ── API-level trigger/preview tests ───────────────────────────────────

class TestTriggerAPI:
    def test_trigger_no_prefs(self, client):
        with patch("briefing.SessionLocal", TestSession):
            resp = client.post("/api/trigger")
        assert resp.status_code == 400

    def test_preview_no_prefs(self, client):
        with patch("briefing.SessionLocal", TestSession):
            resp = client.post("/api/preview")
        assert resp.status_code == 400

    def test_preview_with_prefs(self, client):
        client.post(
            "/api/preferences",
            json={"city": "London", "news_topics": "tech", "telegram_chat_id": ""},
        )
        with patch("briefing.SessionLocal", TestSession):
            resp = client.post("/api/preview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "message" in data
        assert len(data["message"]) > 50
