"""Database models and API schemas for insight-engine."""
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50))          # review | survey | ticket
    text: Mapped[str] = mapped_column(Text)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5, optional
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    # Pipeline outputs
    theme_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("themes.id"), nullable=True
    )
    sentiment: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # -1..1
    urgency: Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # 0..1

    theme: Mapped[Optional["Theme"]] = relationship(back_populates="records")


class Theme(Base):
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    avg_sentiment: Mapped[float] = mapped_column(Float, default=0.0)
    avg_urgency: Mapped[float] = mapped_column(Float, default=0.0)
    suggested_action: Mapped[str] = mapped_column(String(30), default="monitor")

    records: Mapped[list[Feedback]] = relationship(back_populates="theme")


class Brief(Base):
    __tablename__ = "briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    content: Mapped[str] = mapped_column(Text)
    generator: Mapped[str] = mapped_column(String(20), default="template")  # llm | template


# ---------- API schemas ----------

VALID_SOURCES = {"review", "survey", "ticket"}


class FeedbackIn(BaseModel):
    source: str = Field(..., description="review | survey | ticket")
    text: str = Field(..., min_length=3, max_length=5000)
    rating: Optional[int] = Field(None, ge=1, le=5)

    @field_validator("source")
    @classmethod
    def valid_source(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_SOURCES:
            raise ValueError(f"source must be one of {sorted(VALID_SOURCES)}")
        return v

    @field_validator("text")
    @classmethod
    def clean_text(cls, v: str) -> str:
        return v.strip()


class FeedbackOut(BaseModel):
    id: int
    source: str
    text: str
    rating: Optional[int]
    theme_id: Optional[int]
    sentiment: Optional[float]
    urgency: Optional[float]

    model_config = {"from_attributes": True}


class ThemeOut(BaseModel):
    id: int
    label: str
    description: str
    size: int
    avg_sentiment: float
    avg_urgency: float
    suggested_action: str

    model_config = {"from_attributes": True}
