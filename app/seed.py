"""
Database seeder — run once after initial setup:
    uv run python -m app.seed

Safe to re-run: uses get-or-create for all records.
Will not overwrite existing data.
"""

import sys
import bcrypt

from app.config import settings
from app.database import SessionLocal, create_tables
import app.models  # noqa: F401 — registers all models


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def get_or_create(db, model, defaults: dict = None, **kwargs):
    """Fetch a record by kwargs, or create it with kwargs + defaults."""
    instance = db.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    params = {**kwargs, **(defaults or {})}
    instance = model(**params)
    db.add(instance)
    return instance, True


def seed_categories(db):
    from app.models.lookup import Category
    categories = [
        {"name": "LAB",      "description": "Lactic Acid Bacteria ferments (sauerkraut, kimchi, lacto pickles)"},
        {"name": "AAB",      "description": "Acetic Acid Bacteria ferments (vinegars)"},
        {"name": "Kombucha", "description": "Symbiotic culture of bacteria and yeast (SCOBY-based)"},
        {"name": "Yeast",    "description": "Yeast-driven ferments (bread, beer, wine)"},
    ]
    for c in categories:
        _, created = get_or_create(db, Category, name=c["name"], defaults={"description": c["description"]})
        if created:
            print(f"  + Category: {c['name']}")
        else:
            print(f"  = Category exists: {c['name']}")


def seed_statuses(db):
    from app.models.lookup import Status
    statuses = [
        {"name": "active",   "color": "#4db88a"},  # green
        {"name": "stasis",   "color": "#c8a96e"},  # amber
        {"name": "ready",    "color": "#a0c840"},  # lime
        {"name": "stopped",  "color": "#6b6860"},  # grey
        {"name": "failed",   "color": "#e85858"},  # red
    ]
    for s in statuses:
        _, created = get_or_create(db, Status, name=s["name"], defaults={"color": s["color"]})
        if created:
            print(f"  + Status: {s['name']} ({s['color']})")
        else:
            print(f"  = Status exists: {s['name']}")


def seed_vessel_types(db):
    from app.models.lookup import VesselType
    types = ["Jar", "Crock", "Barrel", "Bottle", "Bucket", "Bag", "Tank"]
    for name in types:
        _, created = get_or_create(db, VesselType, name=name)
        if created:
            print(f"  + VesselType: {name}")
        else:
            print(f"  = VesselType exists: {name}")


def seed_vessel_materials(db):
    from app.models.lookup import VesselMaterial
    materials = ["Glass", "Ceramic", "Wood", "Plastic", "Stainless Steel", "Clay", "Enamel"]
    for name in materials:
        _, created = get_or_create(db, VesselMaterial, name=name)
        if created:
            print(f"  + VesselMaterial: {name}")
        else:
            print(f"  = VesselMaterial exists: {name}")


def seed_cut_sizes(db):
    from app.models.lookup import CutSize
    cut_sizes = [
        {"name": "Whole",            "description": "Left entirely intact"},
        {"name": "Halved",           "description": "Cut into two equal parts"},
        {"name": "Quartered",        "description": "Cut into four parts"},
        {"name": "Thinly shredded",  "description": "Very fine strips or shreds"},
        {"name": "Coarsely shredded","description": "Thick strips or shreds"},
        {"name": "Thinly sliced",    "description": "Thin rounds or slices"},
        {"name": "Thickly sliced",   "description": "Thick rounds or slices"},
        {"name": "Cubed",            "description": "Cut into even cubes"},
        {"name": "Roughly chopped",  "description": "Irregular rough pieces"},
        {"name": "Finely chopped",   "description": "Small, fine pieces"},
        {"name": "Powdered",         "description": "Ground to a powder"},
        {"name": "Liquid",           "description": "Already in liquid form"},
    ]
    for c in cut_sizes:
        _, created = get_or_create(db, CutSize, name=c["name"], defaults={"description": c["description"]})
        if created:
            print(f"  + CutSize: {c['name']}")
        else:
            print(f"  = CutSize exists: {c['name']}")


def seed_tags(db):
    from app.models.lookup import Tag
    tags = [
        "Vegetable", "Fruit", "Grain", "Legume", "Meat", "Fish",
        "Dairy", "Liquid", "Herb", "Spice", "Funghi", "Flower",
    ]
    for name in tags:
        _, created = get_or_create(db, Tag, name=name)
        if created:
            print(f"  + Tag: {name}")
        else:
            print(f"  = Tag exists: {name}")


def seed_smell_descriptors(db):
    from app.models.lookup import SmellDescriptor
    descriptors = [
        "Acidic", "Vinegary", "Yeasty", "Funky", "Floral", "Fruity",
        "Earthy", "Sulphurous", "Cheesy", "Alcoholic", "Musty", "Fresh",
        "Sour", "Sweet", "Umami", "Off", "Neutral",
    ]
    for name in descriptors:
        _, created = get_or_create(db, SmellDescriptor, name=name)
        if created:
            print(f"  + SmellDescriptor: {name}")
        else:
            print(f"  = SmellDescriptor exists: {name}")


def seed_visual_descriptors(db):
    from app.models.lookup import VisualDescriptor
    descriptors = [
        "Cloudy", "Clear", "Pellicle forming", "Pellicle healthy", "Pellicle thin",
        "Bubbling actively", "Bubbling slowly", "No activity", "Sediment present",
        "Colour change", "Mould present", "Kahm yeast", "Brine low", "Brine good",
        "Good colour", "Discoloured",
    ]
    for name in descriptors:
        _, created = get_or_create(db, VisualDescriptor, name=name)
        if created:
            print(f"  + VisualDescriptor: {name}")
        else:
            print(f"  = VisualDescriptor exists: {name}")


def seed_admin(db):
    from app.models.user import User, UserRole

    if not settings.ADMIN_PASSWORD:
        print("  ! ADMIN_PASSWORD not set in .env — skipping admin creation")
        return

    _, created = get_or_create(
        db,
        User,
        username=settings.ADMIN_USERNAME,
        defaults={
            "email": settings.ADMIN_EMAIL,
            "hashed_password": hash_password(settings.ADMIN_PASSWORD),
            "role": UserRole.admin,
            "is_active": True,
        },
    )
    if created:
        print(f"  + Admin user: {settings.ADMIN_USERNAME} ({settings.ADMIN_EMAIL})")
    else:
        print(f"  = Admin user exists: {settings.ADMIN_USERNAME}")


def run():
    print("Creating tables...")
    create_tables()

    print("\nSeeding database...")
    db = SessionLocal()
    try:
        print("\n[Categories]")
        seed_categories(db)

        print("\n[Statuses]")
        seed_statuses(db)

        print("\n[Vessel Types]")
        seed_vessel_types(db)

        print("\n[Vessel Materials]")
        seed_vessel_materials(db)

        print("\n[Cut Sizes]")
        seed_cut_sizes(db)

        print("\n[Tags]")
        seed_tags(db)

        print("\n[Smell Descriptors]")
        seed_smell_descriptors(db)

        print("\n[Visual Descriptors]")
        seed_visual_descriptors(db)

        print("\n[Admin User]")
        seed_admin(db)

        db.commit()
        print("\n✓ Seed complete.")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Seed failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    run()