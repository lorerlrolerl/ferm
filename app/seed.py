"""
Database seeder — run once after initial setup:
    uv run python -m app.seed

Safe to re-run: uses get-or-create for all records.
"""

import sys
import bcrypt

from app.config import settings
from app.database import SessionLocal, create_tables
import app.models  # noqa: F401


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def get_or_create(db, model, defaults: dict = None, **kwargs):
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
        print(f"  {'+'if created else '='} Category: {c['name']}")


def seed_statuses(db):
    from app.models.lookup import Status
    statuses = [
        {"name": "active",   "color": "#4db88a"},
        {"name": "stasis",   "color": "#c8a96e"},
        {"name": "ready",    "color": "#a0c840"},
        {"name": "stopped",  "color": "#6b6860"},
        {"name": "failed",   "color": "#e85858"},
    ]
    for s in statuses:
        _, created = get_or_create(db, Status, name=s["name"], defaults={"color": s["color"]})
        print(f"  {'+'if created else '='} Status: {s['name']}")


def seed_vessel_types(db):
    from app.models.lookup import VesselType
    for name in ["Jar", "Crock", "Barrel", "Bottle", "Bucket", "Bag", "Tank"]:
        _, created = get_or_create(db, VesselType, name=name)
        print(f"  {'+'if created else '='} VesselType: {name}")


def seed_vessel_materials(db):
    from app.models.lookup import VesselMaterial
    for name in ["Glass", "Ceramic", "Wood", "Plastic", "Stainless Steel", "Clay", "Enamel"]:
        _, created = get_or_create(db, VesselMaterial, name=name)
        print(f"  {'+'if created else '='} VesselMaterial: {name}")


def seed_cut_sizes(db):
    from app.models.lookup import CutSize
    cut_sizes = [
        {"name": "Whole",             "description": "Left entirely intact"},
        {"name": "Halved",            "description": "Cut into two equal parts"},
        {"name": "Quartered",         "description": "Cut into four parts"},
        {"name": "Thinly Shredded",   "description": "Very fine strips or shreds"},
        {"name": "Coarsely Shredded", "description": "Thick strips or shreds"},
        {"name": "Thinly Sliced",     "description": "Thin rounds or slices"},
        {"name": "Thickly Sliced",    "description": "Thick rounds or slices"},
        {"name": "Cubed",             "description": "Cut into even cubes"},
        {"name": "Roughly Chopped",   "description": "Irregular rough pieces"},
        {"name": "Finely Chopped",    "description": "Small, fine pieces"},
        {"name": "Powdered",          "description": "Ground to a powder"},
        {"name": "Liquid",            "description": "Already in liquid form"},
    ]
    for c in cut_sizes:
        _, created = get_or_create(db, CutSize, name=c["name"], defaults={"description": c["description"]})
        print(f"  {'+'if created else '='} CutSize: {c['name']}")


def seed_tags(db):
    from app.models.lookup import Tag
    for name in ["Vegetable", "Fruit", "Grain", "Legume", "Meat", "Fish",
                 "Dairy", "Liquid", "Herb", "Spice", "Funghi", "Flower"]:
        _, created = get_or_create(db, Tag, name=name)
        print(f"  {'+'if created else '='} Tag: {name}")


def seed_smell_descriptors(db):
    from app.models.lookup import SmellDescriptor
    for name in ["Acidic", "Vinegary", "Yeasty", "Funky", "Floral", "Fruity",
                 "Earthy", "Sulphurous", "Cheesy", "Alcoholic", "Musty", "Fresh",
                 "Sour", "Sweet", "Umami", "Off", "Neutral"]:
        _, created = get_or_create(db, SmellDescriptor, name=name)
        print(f"  {'+'if created else '='} SmellDescriptor: {name}")


def seed_visual_descriptors(db):
    from app.models.lookup import VisualDescriptor
    for name in ["Cloudy", "Clear", "Pellicle forming", "Pellicle healthy", "Pellicle thin",
                 "Bubbling actively", "Bubbling slowly", "No activity", "Sediment present",
                 "Colour change", "Mould present", "Kahm yeast", "Brine low", "Brine good",
                 "Good colour", "Discoloured"]:
        _, created = get_or_create(db, VisualDescriptor, name=name)
        print(f"  {'+'if created else '='} VisualDescriptor: {name}")


def seed_ingredients(db):
    from app.models.lookup import CutSize, Tag
    from app.models.ingredient import Ingredient

    def get_cut(name):
        return db.query(CutSize).filter_by(name=name).first()

    def get_tag(name):
        return db.query(Tag).filter_by(name=name).first()

    vegetable = get_tag("Vegetable")
    herb      = get_tag("Herb")
    liquid    = get_tag("Liquid")

    items = [
        {"name": "White Cabbage", "cut": "Thinly Shredded",   "tags": [vegetable]},
        {"name": "White Cabbage", "cut": "Coarsely Shredded", "tags": [vegetable]},
        {"name": "Red Cabbage",   "cut": "Thinly Shredded",   "tags": [vegetable]},
        {"name": "Red Cabbage",   "cut": "Coarsely Shredded", "tags": [vegetable]},
        {"name": "Black Tea Leaves", "cut": "Liquid",         "tags": [herb]},
        {"name": "Kombucha",      "cut": "Liquid",            "tags": [liquid]},
        {"name": "Water",         "cut": "Liquid",            "tags": [liquid]},
    ]

    for item in items:
        cut = get_cut(item["cut"])
        existing = db.query(Ingredient).filter_by(
            name=item["name"],
            cut_size_id=cut.id if cut else None,
        ).first()
        if existing:
            print(f"  = Ingredient: {item['name']} ({item['cut']})")
            continue
        ing = Ingredient(
            name=item["name"],
            cut_size_id=cut.id if cut else None,
        )
        ing.tags = [t for t in item["tags"] if t]
        db.add(ing)
        print(f"  + Ingredient: {item['name']} ({item['cut']})")


def seed_additives(db):
    from app.models.additive import Additive, AdditiveType

    items = [
        {"name": "SCOBY",       "type": AdditiveType.culture, "description": "Symbiotic culture of bacteria and yeast"},
        {"name": "White Sugar",  "type": AdditiveType.sugar,   "description": "Refined white cane sugar"},
        {"name": "Sea Salt",     "type": AdditiveType.salt,    "description": "Fine sea salt"},
    ]

    for item in items:
        _, created = get_or_create(
            db, Additive,
            name=item["name"],
            additive_type=item["type"],
            defaults={"description": item["description"]},
        )
        print(f"  {'+'if created else '='} Additive: {item['name']} ({item['type'].value})")


def seed_admin(db):
    from app.models.user import User, UserRole
    if not settings.ADMIN_PASSWORD:
        print("  ! ADMIN_PASSWORD not set in .env — skipping admin creation")
        return
    _, created = get_or_create(
        db, User,
        username=settings.ADMIN_USERNAME,
        defaults={
            "email": settings.ADMIN_EMAIL,
            "hashed_password": hash_password(settings.ADMIN_PASSWORD),
            "role": UserRole.admin,
            "is_active": True,
        },
    )
    print(f"  {'+'if created else '='} Admin: {settings.ADMIN_USERNAME} ({settings.ADMIN_EMAIL})")


def run():
    print("Creating tables...")
    create_tables()

    print("\nSeeding database...")
    db = SessionLocal()
    try:
        print("\n[Categories]");      seed_categories(db)
        print("\n[Statuses]");        seed_statuses(db)
        print("\n[Vessel Types]");    seed_vessel_types(db)
        print("\n[Vessel Materials]");seed_vessel_materials(db)
        print("\n[Cut Sizes]");       seed_cut_sizes(db)
        print("\n[Tags]");            seed_tags(db)
        print("\n[Smell Descriptors]");  seed_smell_descriptors(db)
        print("\n[Visual Descriptors]"); seed_visual_descriptors(db)
        print("\n[Ingredients]");     seed_ingredients(db)
        print("\n[Additives]");       seed_additives(db)
        print("\n[Admin User]");      seed_admin(db)

        db.commit()
        print("\n✓ Seed complete.")
    except Exception as e:
        db.rollback()
        print(f"\n✗ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()