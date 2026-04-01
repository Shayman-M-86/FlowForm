#!/usr/bin/env python3
"""Generate secret files in a ./secrets subfolder next to this script."""

from __future__ import annotations

from pathlib import Path
import argparse
import secrets
import string

# =========================
# Settings
# =========================

DEFAULT_ENVIRONMENTS = ("dev", "test")
ALLOW_PROD_GENERATION = False  # Only change this in the file.
PROD_ENVIRONMENT = "prod"

SECRETS = {
    "DATABASE_CORE_APP_PASSWORD": 32,
    "DATABASE_CORE_INIT_PASSWORD": 32,
    "DATABASE_RESPONSE_APP_PASSWORD": 32,
    "DATABASE_RESPONSE_INIT_PASSWORD": 32,
    "FLOWFORM_APP_SECRET_KEY": 64,
}

OVERWRITE_EXISTING = False
SECRETS_DIR_NAME = "secrets"

# First and last character must be alphanumeric
EDGE_ALPHABET = string.ascii_letters + string.digits

# Middle characters stay URI-safe for DB connection strings
MIDDLE_ALPHABET = string.ascii_letters + string.digits + "-._~"


def generate_secret(length: int) -> str:
    """Generate a secret with alphanumeric first and last characters."""
    if length < 2:
        raise ValueError("Secret length must be at least 2.")

    first = secrets.choice(EDGE_ALPHABET)
    last = secrets.choice(EDGE_ALPHABET)
    middle = "".join(secrets.choice(MIDDLE_ALPHABET) for _ in range(length - 2))
    return f"{first}{middle}{last}"


def build_filename(secret_name: str, environment: str) -> str:
    """Return the filename for a secret/environment pair."""
    return f"{secret_name}.{environment}.secret.txt"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate secret files for selected environments."
    )
    parser.add_argument(
        "environments",
        nargs="*",
        choices=("dev", "test", "all"),
        help="Which environments to generate: dev, test, or all.",
    )
    return parser.parse_args()


def resolve_environments(args: argparse.Namespace) -> tuple[str, ...]:
    """Resolve which environments should be generated."""
    if not args.environments:
        environments = DEFAULT_ENVIRONMENTS
    elif "all" in args.environments:
        environments = ("dev", "test")
    else:
        environments = tuple(dict.fromkeys(args.environments))

    if ALLOW_PROD_GENERATION:
        environments = tuple(dict.fromkeys((*environments, PROD_ENVIRONMENT)))

    return environments


def main() -> None:
    args = parse_args()
    environments = resolve_environments(args)

    script_dir = Path(__file__).resolve().parent
    secrets_dir = script_dir / SECRETS_DIR_NAME
    secrets_dir.mkdir(exist_ok=True)

    created_files: list[Path] = []
    skipped_files: list[Path] = []

    for environment in environments:
        for secret_name, length in SECRETS.items():
            filename = build_filename(secret_name, environment)
            filepath = secrets_dir / filename

            if filepath.exists() and not OVERWRITE_EXISTING:
                skipped_files.append(filepath)
                continue

            secret_value = generate_secret(length)
            filepath.write_text(secret_value + "\n", encoding="utf-8")
            created_files.append(filepath)

    if created_files:
        print("Created files:")
        for path in created_files:
            print(f"  - {path}")

    if skipped_files:
        print("\nSkipped existing files:")
        for path in skipped_files:
            print(f"  - {path}")


if __name__ == "__main__":
    main()
