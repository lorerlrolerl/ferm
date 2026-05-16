from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Many-to-many: observation ↔ smell descriptor
observation_smells = Table(
    "observation_smells",
    Base.metadata,
    Column("observation_id", Integer, ForeignKey("observations.id"), primary_key=True),
    Column("smell_descriptor_id", Integer, ForeignKey("smell_descriptors.id"), primary_key=True),
)

# Many-to-many: observation ↔ visual descriptor
observation_visuals = Table(
    "observation_visuals",
    Base.metadata,
    Column("observation_id", Integer, ForeignKey("observations.id"), primary_key=True),
    Column("visual_descriptor_id", Integer, ForeignKey("visual_descriptors.id"), primary_key=True),
)


class Observation(Base):
    """
    A timestamped log entry of smell and/or visual descriptors
    for a batch or container, optionally with free-text notes.
    """
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)  # 'batch' or 'container'
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    observed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    observed_by_user: Mapped["User"] = relationship(back_populates="observations")
    smell_descriptors: Mapped[list["SmellDescriptor"]] = relationship(secondary=observation_smells)
    visual_descriptors: Mapped[list["VisualDescriptor"]] = relationship(secondary=observation_visuals)

    def __repr__(self) -> str:
        return f"<Observation on {self.target_type}:{self.target_id} at {self.observed_at}>"