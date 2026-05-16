from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Tool(Base):
    """
    A physical tool used in the kitchen: pH meter, thermometer, refractometer, etc.
    Maintenance is handled via the Schedule system (target_type='tool', target_id=tool.id).
    """
    __tablename__ = "tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_type: Mapped[str] = mapped_column(String(64), nullable=False)  # 'ph_meter', 'thermometer', etc.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    measurements: Mapped[list["Measurement"]] = relationship(back_populates="tool")

    def __repr__(self) -> str:
        return f"<Tool {self.name} ({self.tool_type})>"
