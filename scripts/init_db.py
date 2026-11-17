"""Create the Curio database tables.

Usage (from the project root):
    python -m scripts.init_db
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as a plain script: `python scripts/init_db.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.database import init_db  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialise the Curio database.")
    parser.parse_args()

    settings = get_settings()
    init_db()
    print(f"Database ready: {settings.database_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
