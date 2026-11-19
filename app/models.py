from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime,
    ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    habits = relationship(
        "Habit",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="habits")
    records = relationship(
        "Record",
        back_populates="habit",
        cascade="all, delete-orphan"
    )


class Record(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True)
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    is_done = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("habit_id", "date", name="uq_habit_record_date"),
    )

    habit = relationship("Habit", back_populates="records")
