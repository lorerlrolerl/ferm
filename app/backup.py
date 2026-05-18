"""
Database backup utility.
Creates a timestamped copy of ferm.db in a backups/ directory.

Usage:
    uv run python -m app.backup           # backup
    uv run python -m app.backup restore   # list and restore
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path

from app.config import settings

BACKUP_DIR = Path(settings.DATABASE_URL.replace("sqlite:///", "")).parent / "backups"


def backup():
    db_path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
    if not db_path.exists():
        print(f"✗ No database found at {db_path}")
        sys.exit(1)

    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"ferm_{timestamp}.db"
    shutil.copy2(db_path, dest)
    size = dest.stat().st_size / 1024
    print(f"✓ Backup saved: {dest} ({size:.1f} KB)")


def list_backups():
    if not BACKUP_DIR.exists():
        print("No backups directory found.")
        return []
    backups = sorted(BACKUP_DIR.glob("ferm_*.db"), reverse=True)
    if not backups:
        print("No backups found.")
        return []
    print(f"{'#':<4} {'File':<40} {'Size':>8}  Created")
    print("─" * 70)
    for i, f in enumerate(backups):
        size = f.stat().st_size / 1024
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{i:<4} {f.name:<40} {size:>6.1f}KB  {mtime}")
    return backups


def restore():
    backups = list_backups()
    if not backups:
        return

    try:
        idx = int(input("\nEnter # to restore (Ctrl+C to cancel): "))
        chosen = backups[idx]
    except (ValueError, IndexError, KeyboardInterrupt):
        print("Cancelled.")
        return

    db_path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))

    # Auto-backup current db before restoring
    if db_path.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pre = BACKUP_DIR / f"ferm_pre_restore_{ts}.db"
        shutil.copy2(db_path, pre)
        print(f"  Current db backed up to: {pre.name}")

    shutil.copy2(chosen, db_path)
    print(f"✓ Restored from: {chosen.name}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        restore()
    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        list_backups()
    else:
        backup()