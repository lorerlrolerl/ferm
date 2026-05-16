from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AuditLog(Base):
    """
    Immutable log of every create, update, and delete action.
    target_type: the model name (e.g. 'ferment', 'batch', 'ingredient')
    target_id: the id of the affected record
    action: 'create', 'update', 'delete'
    changes: JSON string of before/after values for updates
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)  # 'create', 'update', 'delete'
    changes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: {"field": [old, new], ...}
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["User | None"] = relationship(back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.target_type}:{self.target_id} by user:{self.user_id}>"
