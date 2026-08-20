from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JobCategory(str, enum.Enum):
    NOTIFICATION = "notification"
    ADMIT_CARD = "admit_card"
    RESULT = "result"
    ANSWER_KEY = "answer_key"
    SYLLABUS = "syllabus"
    EDUCATION = "education"


class JobScope(str, enum.Enum):
    ALL_INDIA = "all_india"
    CENTRAL = "central"
    STATE = "state"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    organization: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[JobCategory] = mapped_column(Enum(JobCategory), nullable=False, index=True)
    scope: Mapped[JobScope] = mapped_column(Enum(JobScope), default=JobScope.ALL_INDIA)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    vacancies: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    apply_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    published_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    exam_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    qualification: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notification_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    age_limit: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    application_fee: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    sections_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class NewsItem(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="general")
    is_important: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
