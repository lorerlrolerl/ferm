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


def log(created, label):
    print(f"  {'+'if created else '='} {label}")


def with_session(fn):
    """Run fn(db) in its own session, commit, close."""
    db = SessionLocal()
    try:
        fn(db)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"  ! Error: {e}")
        raise
    finally:
        db.close()


def get_or_create(db, model, defaults=None, **kwargs):
    instance = db.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    instance = model(**{**kwargs, **(defaults or {})})
    db.add(instance)
    return instance, True


# ── Lookup tables ──────────────────────────────────────────────────────────

def seed_categories(db):
    from app.models.lookup import Category
    for name, desc in [
        ("LAB",      "Lactic Acid Bacteria ferments (sauerkraut, kimchi, lacto pickles)"),
        ("AAB",      "Acetic Acid Bacteria ferments (vinegars)"),
        ("Kombucha", "Symbiotic culture of bacteria and yeast (SCOBY-based)"),
        ("Yeast",    "Yeast-driven ferments (bread, beer, wine)"),
    ]:
        _, c = get_or_create(db, Category, name=name, defaults={"description": desc})
        log(c, f"Category: {name}")


def seed_statuses(db):
    from app.models.lookup import Status
    for name, color in [
        ("active", "#4db88a"), ("stasis", "#c8a96e"), ("ready", "#a0c840"),
        ("stopped", "#6b6860"), ("failed", "#e85858"),
    ]:
        _, c = get_or_create(db, Status, name=name, defaults={"color": color})
        log(c, f"Status: {name}")


def seed_cut_sizes(db):
    from app.models.lookup import CutSize
    for name, desc in [
        ("Whole",             "Left entirely intact"),
        ("Halved",            "Cut into two equal parts"),
        ("Quartered",         "Cut into four parts"),
        ("Thinly Shredded",   "Very fine strips or shreds"),
        ("Coarsely Shredded", "Thick strips or shreds"),
        ("Thinly Sliced",     "Thin rounds or slices"),
        ("Thickly Sliced",    "Thick rounds or slices"),
        ("Cubed",             "Cut into even cubes"),
        ("Roughly Chopped",   "Irregular rough pieces"),
        ("Finely Chopped",    "Small, fine pieces"),
        ("Powdered",          "Ground to a powder"),
        ("Liquid",            "Already in liquid form"),
    ]:
        _, c = get_or_create(db, CutSize, name=name, defaults={"description": desc})
        log(c, f"CutSize: {name}")


def seed_tags(db):
    from app.models.lookup import Tag
    for name in ["Vegetable","Fruit","Grain","Legume","Meat","Fish",
                 "Dairy","Liquid","Herb","Spice","Funghi","Flower"]:
        _, c = get_or_create(db, Tag, name=name)
        log(c, f"Tag: {name}")


def seed_smell_descriptors(db):
    from app.models.lookup import SmellDescriptor
    for name in ["Acidic","Vinegary","Yeasty","Funky","Floral","Fruity",
                 "Earthy","Sulphurous","Cheesy","Alcoholic","Musty","Fresh",
                 "Sour","Sweet","Umami","Off","Neutral"]:
        _, c = get_or_create(db, SmellDescriptor, name=name)
        log(c, f"SmellDescriptor: {name}")


def seed_visual_descriptors(db):
    from app.models.lookup import VisualDescriptor
    for name in ["Cloudy","Clear","Pellicle forming","Pellicle healthy","Pellicle thin",
                 "Bubbling actively","Bubbling slowly","No activity","Sediment present",
                 "Colour change","Mould present","Kahm yeast","Brine low","Brine good",
                 "Good colour","Discoloured"]:
        _, c = get_or_create(db, VisualDescriptor, name=name)
        log(c, f"VisualDescriptor: {name}")


def seed_vessel_types(db):
    from app.models.lookup import VesselType
    for name in ["Jar","Crock","Barrel","Bottle","Bucket","Bag","Tank"]:
        _, c = get_or_create(db, VesselType, name=name)
        log(c, f"VesselType: {name}")


def seed_vessel_materials(db):
    from app.models.lookup import VesselMaterial
    for name in ["Glass","Ceramic","Wood","Plastic","Stainless Steel","Clay","Enamel"]:
        _, c = get_or_create(db, VesselMaterial, name=name)
        log(c, f"VesselMaterial: {name}")


# ── Ingredients — one session per ingredient to avoid identity map issues ──

def seed_one_ingredient(name, cut_name, tag_names):
    """Each ingredient gets its own isolated session."""
    from app.models.lookup import CutSize, Tag
    from app.models.ingredient import Ingredient

    db = SessionLocal()
    try:
        cs = db.query(CutSize).filter_by(name=cut_name).first()
        if not cs:
            print(f"  ! CutSize '{cut_name}' not found — skipping {name}")
            return

        existing = db.query(Ingredient).filter(
            Ingredient.name == name,
            Ingredient.cut_size_id == cs.id,
        ).first()

        tags = [t for t in [db.query(Tag).filter_by(name=n).first() for n in tag_names] if t]

        if existing:
            existing.is_active = True
            existing.tags = tags
            db.commit()
            log(False, f"Ingredient: {name} ({cut_name})")
        else:
            ing = Ingredient(name=name, cut_size_id=cs.id, is_active=True)
            db.add(ing)
            db.flush()   # get ing.id before writing join table
            ing.tags = tags
            db.commit()
            log(True, f"Ingredient: {name} ({cut_name})")
    except Exception as e:
        db.rollback()
        print(f"  ! Failed {name} ({cut_name}): {e}")
    finally:
        db.close()


def seed_ingredients():
    """No db param — manages its own sessions internally."""
    items = [
        ("White Cabbage",    "Coarsely Shredded", ["Vegetable"]),
        ("White Cabbage",    "Thinly Shredded",   ["Vegetable"]),
        ("Red Cabbage",      "Coarsely Shredded", ["Vegetable"]),
        ("Red Cabbage",      "Thinly Shredded",   ["Vegetable"]),
        ("Black Tea Leaves", "Whole",              ["Herb"]),
        ("Water",            "Whole",              ["Liquid"]),
    ]
    for name, cut_name, tag_names in items:
        seed_one_ingredient(name, cut_name, tag_names)


# ── Additives ──────────────────────────────────────────────────────────────

def seed_additives(db):
    from app.models.additive import Additive, AdditiveType
    for name, atype, desc in [
        ("SCOBY",              AdditiveType.culture,   "Symbiotic culture of bacteria and yeast"),
        ("Brown Sugar",        AdditiveType.sugar,     "Unrefined brown cane sugar"),
        ("Keltisch Fine Salt", AdditiveType.salt,      "Fine Celtic grey salt"),
        ("Backslop Kombucha",  AdditiveType.backslopp, None),
    ]:
        _, c = get_or_create(db, Additive, name=name, additive_type=atype,
                             defaults={"description": desc})
        log(c, f"Additive: {name} ({atype.value})")


# ── Admin user ─────────────────────────────────────────────────────────────

def seed_admin(db):
    from app.models.user import User, UserRole
    if not settings.ADMIN_PASSWORD:
        print("  ! ADMIN_PASSWORD not set in .env — skipping")
        return
    _, c = get_or_create(
        db, User,
        username=settings.ADMIN_USERNAME,
        defaults={
            "email": settings.ADMIN_EMAIL,
            "hashed_password": hash_password(settings.ADMIN_PASSWORD),
            "role": UserRole.admin,
            "is_active": True,
        },
    )
    log(c, f"Admin: {settings.ADMIN_USERNAME} ({settings.ADMIN_EMAIL})")


# ── Main ───────────────────────────────────────────────────────────────────

def run():
    print("Creating tables...")
    create_tables()
    print("\nSeeding database...")

    # All lookup tables share one session
    def seed_lookups(db):
        print("\n[Categories]");          seed_categories(db)
        print("\n[Statuses]");            seed_statuses(db)
        print("\n[Cut Sizes]");           seed_cut_sizes(db)
        print("\n[Tags]");               seed_tags(db)
        print("\n[Smell Descriptors]");  seed_smell_descriptors(db)
        print("\n[Visual Descriptors]"); seed_visual_descriptors(db)
        print("\n[Vessel Types]");       seed_vessel_types(db)
        print("\n[Vessel Materials]");   seed_vessel_materials(db)

    with_session(seed_lookups)

    # Ingredients — each manages its own session
    print("\n[Ingredients]")
    seed_ingredients()

    # Additives and admin share one session
    def seed_rest(db):
        print("\n[Additives]");   seed_additives(db)
        print("\n[Admin User]"); seed_admin(db)

    with_session(seed_rest)

    print("\n✓ Seed complete.")


if __name__ == "__main__":
    run()