from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MeasurementType(PyEnum):
    ph = "ph"
    temperature = "temperature"


class TargetType(PyEnum):
    batch = "batch"
    container = "container"


class Measurement(Base):
    """
    A single pH or temperature reading, attached to a batch or container.
    When a pH reading crosses a batch's target_ph, the UI surfaces a
    'mark as ready?' suggestion — human still confirms via status change.
    """
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)  # 'batch' or 'container'
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    measurement_type: Mapped[MeasurementType] = mapped_column(Enum(MeasurementType), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)  # 'pH', '°C', '°F'
    tool_id: Mapped[int | None] = mapped_column(ForeignKey("tools.id"), nullable=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    measured_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tool: Mapped["Tool | None"] = relationship()
    measured_by_user: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return f"<Measurement {self.measurement_type.value}={self.value}{self.unit} on {self.target_type}:{self.target_id}>"
