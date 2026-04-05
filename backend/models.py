from sqlalchemy import Column, Integer, String
from database import Base


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, nullable=False, default="London")
    news_topics = Column(String, nullable=False, default="technology")
    telegram_chat_id = Column(String, nullable=False, default="")


class ClassSchedule(Base):
    __tablename__ = "class_schedule"

    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(String, nullable=False)  # Monday, Tuesday, ...
    time = Column(String, nullable=False)          # e.g. "09:00"
    subject = Column(String, nullable=False)
    location = Column(String, nullable=False, default="")
