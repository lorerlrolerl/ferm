from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AdditiveType(PyEnum):
    salt = "salt"
    backslopp = "backslopp"
    culture = "culture"
    sugar = "sugar"
    spice = "spice"
    other = "other"


class Additive(Base):
    """
    Non-ingredient additions: salts, backslops, cultures, etc.
    Tracked separately from ingredients as they play a different role.
    Protected from deletion if used in any batch.
    """
    __tablename__ = "additives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    additive_type: Mapped[AdditiveType] = mapped_column(Enum(AdditiveType), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    batch_additives: Mapped[list["BatchAdditive"]] = relationship(back_populates="additive")

    @property
    def is_in_use(self) -> bool:
        return len(self.batch_additives) > 0

    def __repr__(self) -> str:
        return f"<Additive {self.name} ({self.additive_type.value})>"
