# Import all models so SQLAlchemy registers them before create_tables() runs.
# Order matters for forward references — keep this order.

from app.models.user import User
from app.models.lookup import (
    Category,
    Status,
    CutSize,
    Tag,
    SmellDescriptor,
    VisualDescriptor,
    VesselType,
    VesselMaterial,
)
from app.models.tool import Tool
from app.models.ingredient import Ingredient, ingredient_tags
from app.models.additive import Additive
from app.models.ferment import Ferment, Batch, Container, BatchIngredient, BatchAdditive
from app.models.measurement import Measurement
from app.models.observation import Observation, observation_smells, observation_visuals
from app.models.schedule import Schedule, ScheduleEvent
from app.models.audit import AuditLog

__all__ = [
    "User",
    "Category", "Status", "CutSize", "Tag",
    "SmellDescriptor", "VisualDescriptor",
    "VesselType", "VesselMaterial",
    "Tool",
    "Ingredient", "ingredient_tags",
    "Additive",
    "Ferment", "Batch", "Container", "BatchIngredient", "BatchAdditive",
    "Measurement",
    "Observation", "observation_smells", "observation_visuals",
    "Schedule", "ScheduleEvent",
    "AuditLog",
]
