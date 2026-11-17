"""Create the Curio database tables.

Usage (from the project root):
    python -m scripts.init_db            # create tables only
    python -m scripts.init_db --demo     # also create a demo account with sample data
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as a plain script: `python scripts/init_db.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialise the Curio database.")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="create a demo user (username 'demo') with sample items and collections",
    )
    args = parser.parse_args()

    settings = get_settings()
    init_db()
    print(f"Database ready: {settings.database_url}")

    if args.demo:
        from app.services.demo_data import create_demo_account

        with SessionLocal() as db:
            _created, message = create_demo_account(db)
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
