from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer,
    String, Text, func, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Ferment ────────────────────────────────────────────────────────────────

class Ferment(Base):
    __tablename__ = "ferments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_ongoing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    status_id: Mapped[int | None] = mapped_column(ForeignKey("statuses.id"), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    category: Mapped["Category"] = relationship(back_populates="ferments")
    status: Mapped["Status"] = relationship()
    created_by_user: Mapped["User"] = relationship(back_populates="created_ferments")
    batches: Mapped[list["Batch"]] = relationship(back_populates="ferment", order_by="Batch.started_at", cascade="all, delete-orphan")
    schedules: Mapped[list["Schedule"]] = relationship(cascade="all, delete-orphan",
        primaryjoin="and_(Schedule.target_id == foreign(Ferment.id), Schedule.target_type == 'ferment')",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<Ferment {self.name}>"


# ── Batch ──────────────────────────────────────────────────────────────────

class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ferment_id: Mapped[int] = mapped_column(ForeignKey("ferments.id"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    batch_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Sequential per ferment: batch 1, 2, 3... regardless of stage
    lot_code: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    # e.g. HSKR-LAB-250516-S1-B1 — auto-suggested, editable
    stage: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"), nullable=True)
    status_id: Mapped[int | None] = mapped_column(ForeignKey("statuses.id"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    target_ready_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    target_ph: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    ferment: Mapped["Ferment"] = relationship(back_populates="batches")
    status: Mapped["Status"] = relationship()
    created_by_user: Mapped["User"] = relationship(back_populates="created_batches")
    parent_batch: Mapped["Batch | None"] = relationship(remote_side="Batch.id", foreign_keys=[parent_batch_id])
    child_batches: Mapped[list["Batch"]] = relationship(foreign_keys=[parent_batch_id], overlaps="parent_batch", cascade="all, delete-orphan")
    logs: Mapped[list["BatchLog"]] = relationship(back_populates="batch", order_by="BatchLog.logged_at.desc()", cascade="all, delete-orphan")
    containers: Mapped[list["Container"]] = relationship(back_populates="batch", cascade="all, delete-orphan")
    ingredients: Mapped[list["BatchIngredient"]] = relationship(back_populates="batch", cascade="all, delete-orphan")
    additives: Mapped[list["BatchAdditive"]] = relationship(back_populates="batch", cascade="all, delete-orphan")
    observations: Mapped[list["Observation"]] = relationship(
        primaryjoin="and_(Observation.target_id == foreign(Batch.id), Observation.target_type == 'batch')",
        viewonly=True,
    )
    measurements: Mapped[list["Measurement"]] = relationship(
        primaryjoin="and_(Measurement.target_id == foreign(Batch.id), Measurement.target_type == 'batch')",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<Batch {self.lot_code or f'B{self.batch_number}'} (ferment_id={self.ferment_id})>"


# ── Batch join tables ──────────────────────────────────────────────────────

class BatchIngredient(Base):
    __tablename__ = "batch_ingredients"
    __table_args__ = (UniqueConstraint("batch_id", "ingredient_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    batch: Mapped["Batch"] = relationship(back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship(back_populates="batch_ingredients")


class BatchAdditive(Base):
    __tablename__ = "batch_additives"
    __table_args__ = (UniqueConstraint("batch_id", "additive_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)
    additive_id: Mapped[int] = mapped_column(ForeignKey("additives.id"), nullable=False)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    batch: Mapped["Batch"] = relationship(back_populates="additives")
    additive: Mapped["Additive"] = relationship(back_populates="batch_additives")


# ── Container ──────────────────────────────────────────────────────────────

class Container(Base):
    __tablename__ = "containers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    vessel_type_id: Mapped[int | None] = mapped_column(ForeignKey("vessel_types.id"), nullable=True)
    vessel_material_id: Mapped[int | None] = mapped_column(ForeignKey("vessel_materials.id"), nullable=True)
    capacity: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fill_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    fill_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status_id: Mapped[int | None] = mapped_column(ForeignKey("statuses.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    batch: Mapped["Batch"] = relationship(back_populates="containers")
    vessel_type: Mapped["VesselType"] = relationship(back_populates="containers")
    vessel_material: Mapped["VesselMaterial"] = relationship(back_populates="containers")
    status: Mapped["Status"] = relationship()
    observations: Mapped[list["Observation"]] = relationship(
        primaryjoin="and_(Observation.target_id == foreign(Container.id), Observation.target_type == 'container')",
        viewonly=True,
    )
    measurements: Mapped[list["Measurement"]] = relationship(
        primaryjoin="and_(Measurement.target_id == foreign(Container.id), Measurement.target_type == 'container')",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<Container {self.name} (batch_id={self.batch_id})>"