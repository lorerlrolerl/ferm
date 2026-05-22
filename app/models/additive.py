from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from app.models.ferment import BatchAdditive


class AdditiveType(Base):
    __tablename__ = "additive_types"

    id:          Mapped[int]          = mapped_column(Integer, primary_key=True)
    name:        Mapped[str]          = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[Optional[str]]= mapped_column(Text, nullable=True)

    additives: Mapped[list["Additive"]] = relationship(back_populates="type_obj")


class Additive(Base):
    __tablename__ = "additives"

    id:               Mapped[int]           = mapped_column(Integer, primary_key=True)
    name:             Mapped[str]           = mapped_column(String(128), nullable=False)
    additive_type_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("additive_types.id"), nullable=True)
    description:      Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    type_obj: Mapped[Optional[AdditiveType]] = relationship(back_populates="additives")

    # Keep old column for backwards compat during transition
    # additive_type: legacy enum string — still in db but no longer used in code

    @property
    def additive_type_name(self) -> str:
        return self.type_obj.name if self.type_obj else "other"

    batch_additives: Mapped[list["BatchAdditive"]] = relationship(back_populates="additive")