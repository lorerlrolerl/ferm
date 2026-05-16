from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Schedule(Base):
    """
    A recurring or one-off maintenance schedule attached to a ferment,
    batch, or container (e.g. feed sourdough every 7 days, burp kombucha jars).

    interval_days: if set, this is a repeating schedule (e.g. every 7 days).
    next_due_at: updated after each ScheduleEvent is logged.

    Missing a scheduled event is allowed — the event log records when it
    actually happened vs when it was due, and notes can explain why.
    """
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)  # 'ferment', 'batch', 'container', 'tool'
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    interval_days: Mapped[float | None] = mapped_column(Float, nullable=True)  # null = one-off or manually triggered
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    events: Mapped[list["ScheduleEvent"]] = relationship(
        back_populates="schedule",
        order_by="ScheduleEvent.due_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Schedule '{self.name}' on {self.target_type}:{self.target_id}>"


class ScheduleEvent(Base):
    """
    A single occurrence of a schedule — planned vs actual.
    due_at: when it was supposed to happen.
    completed_at: when it actually happened (may be earlier or later).
    was_late: computed flag, True if completed_at > due_at.
    notes: what was done, why it was early/late, any observations.
    """
    __tablename__ = "schedule_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id"), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    was_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    schedule: Mapped["Schedule"] = relationship(back_populates="events")
    completed_by_user: Mapped["User | None"] = relationship(back_populates="schedule_events")

    def __repr__(self) -> str:
        status = "done" if self.completed_at else "pending"
        return f"<ScheduleEvent due={self.due_at} [{status}]>"
