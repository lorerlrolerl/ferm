from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    """Fermentation category: LAB, AAB, Kombucha, Yeast."""
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    ferments: Mapped[list["Ferment"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.name}>"


class Status(Base):
    """Ferment/batch/container status: active, ready, failed, stopped, stasis."""
    __tablename__ = "statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#888888")
    # color is a hex string e.g. "#4db88a"

    def __repr__(self) -> str:
        return f"<Status {self.name}>"


class CutSize(Base):
    """How an ingredient is prepared: thinly shredded, cubed, whole, powdered, ..."""
    __tablename__ = "cut_sizes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    ingredients: Mapped[list["Ingredient"]] = relationship(back_populates="cut_size")

    def __repr__(self) -> str:
        return f"<CutSize {self.name}>"


class Tag(Base):
    """Ingredient tags: vegetable, liquid, meat, grain, ..."""
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"


class SmellDescriptor(Base):
    """Vocabulary for smell observations: acidic, floral, funky, ..."""
    __tablename__ = "smell_descriptors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<SmellDescriptor {self.name}>"


class VisualDescriptor(Base):
    """Vocabulary for visual observations: cloudy, pellicle forming, ..."""
    __tablename__ = "visual_descriptors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<VisualDescriptor {self.name}>"


class VesselType(Base):
    """Type of vessel: jar, crock, barrel, bottle, ..."""
    __tablename__ = "vessel_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    containers: Mapped[list["Container"]] = relationship(back_populates="vessel_type")

    def __repr__(self) -> str:
        return f"<VesselType {self.name}>"


class VesselMaterial(Base):
    """Material of vessel: glass, ceramic, wood, plastic, ..."""
    __tablename__ = "vessel_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    containers: Mapped[list["Container"]] = relationship(back_populates="vessel_material")

    def __repr__(self) -> str:
        return f"<VesselMaterial {self.name}>"
