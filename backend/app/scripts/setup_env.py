"""
Creates backend/.env from .env.example (if it doesn't exist yet) with a freshly
generated random JWT secret. Safe to run repeatedly -- never overwrites an
existing .env.

    python -m app.scripts.setup_env
"""
from __future__ import annotations

import secrets
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]


def main(backend_dir: Path = BACKEND) -> int:
    env, example = backend_dir / ".env", backend_dir / ".env.example"
    if env.exists():
        print(f".env already exists at {env} -- left unchanged.")
        return 0
    if not example.exists():
        print(f"ERROR: {example} not found.")
        return 1
    text = example.read_text(encoding="utf-8")
    text = text.replace("JWT_SECRET_KEY=change-this-to-a-long-random-string", f"JWT_SECRET_KEY={secrets.token_urlsafe(48)}")
    env.write_text(text, encoding="utf-8")
    print(f"Created {env} (SQLite database, new random JWT secret).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
