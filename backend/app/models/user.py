from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    preferences: Mapped[Optional["UserPreferences"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    profile: Mapped[Optional["UserProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    favorites: Mapped[list["FavoriteJob"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    states: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    categories: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    qualifications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    organizations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    whatsapp_alerts: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_frequency: Mapped[str] = mapped_column(String(20), default="instant")

    user: Mapped["User"] = relationship(back_populates="preferences")


class UserProfile(Base):
    """Candidate profile for personalized job matching."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # UR/OBC/SC/ST/EWS
    current_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    highest_qualification: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    education_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    experience_years: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    experience_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    skills: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    preferred_posts: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    preferred_departments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="profile")


class FavoriteJob(Base):
    __tablename__ = "favorite_jobs"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_job"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="favorites")


class AlertLog(Base):
    __tablename__ = "alert_logs"
    __table_args__ = (UniqueConstraint("user_id", "job_id", "channel", name="uq_alert"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(20))  # email | whatsapp
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
