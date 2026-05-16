from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Many-to-many: ingredient ↔ tag
ingredient_tags = Table(
    "ingredient_tags",
    Base.metadata,
    Column("ingredient_id", Integer, ForeignKey("ingredients.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class Ingredient(Base):
    """
    A specific ingredient in a specific preparation.
    'Cabbage cubed' and 'Cabbage thinly shredded' are distinct ingredients.
    Protected from deletion if used in any batch.
    """
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cut_size_id: Mapped[int | None] = mapped_column(ForeignKey("cut_sizes.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    cut_size: Mapped["CutSize"] = relationship(back_populates="ingredients")
    tags: Mapped[list["Tag"]] = relationship(secondary=ingredient_tags)
    batch_ingredients: Mapped[list["BatchIngredient"]] = relationship(back_populates="ingredient")

    @property
    def is_in_use(self) -> bool:
        """True if this ingredient is referenced by any batch."""
        return len(self.batch_ingredients) > 0

    def __repr__(self) -> str:
        cut = f" ({self.cut_size.name})" if self.cut_size else ""
        return f"<Ingredient {self.name}{cut}>"