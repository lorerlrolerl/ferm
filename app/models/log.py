"""
BatchLog — one unified log entry per session combining:
  - status change (optional)
  - pH measurement (optional)
  - temperature measurement (optional)
  - smell descriptors + free notes (optional)
  - visual descriptors + free notes (optional)
  - general notes
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

# Many-to-many: log entry ↔ smell descriptor
log_smells = Table(
    "log_smells", Base.metadata,
    Column("log_id", Integer, ForeignKey("batch_logs.id"), primary_key=True),
    Column("smell_id", Integer, ForeignKey("smell_descriptors.id"), primary_key=True),
)

# Many-to-many: log entry ↔ visual descriptor
log_visuals = Table(
    "log_visuals", Base.metadata,
    Column("log_id", Integer, ForeignKey("batch_logs.id"), primary_key=True),
    Column("visual_id", Integer, ForeignKey("visual_descriptors.id"), primary_key=True),
)


class BatchLog(Base):
    __tablename__ = "batch_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    logged_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Status change — if set, also updates batch.status_id
    status_id: Mapped[int | None] = mapped_column(ForeignKey("statuses.id"), nullable=True)

    # Measurements
    ph: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Observations
    smell_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    batch = relationship("Batch", back_populates="logs")
    logged_by = relationship("User")
    status = relationship("Status")
    smell_descriptors = relationship("SmellDescriptor", secondary=log_smells)
    visual_descriptors = relationship("VisualDescriptor", secondary=log_visuals)

    def __repr__(self) -> str:
        return f"<BatchLog batch={self.batch_id} at={self.logged_at}>"