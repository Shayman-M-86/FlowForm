#!/usr/bin/env python3
"""Generate throwaway secret files for the dev/test Docker environments.

Only machine-local, regenerable values are produced here — the local
Postgres passwords and (for test) the Flask secret key. Values that must
persist or cannot be generated (Flask dev secret key, Auth0 management
secret) live in AWS Secrets Manager and are fetched by
scripts/infra/fetch-dev-secrets.sh instead.

Prod values are deliberately NOT generatable: prod secrets are created and
stored in Secrets Manager only, never as local files.

Usage:
    scripts/infra/generate-secrets.sh dev
    scripts/infra/generate-secrets.sh test --output-dir "$FLOWFORM_SECRET_DIR"

Existing files are never overwritten; delete a file to rotate it.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import secrets
import string

DEFAULT_ENVIRONMENTS = ("dev", "test")

# Default output keeps dev's DB passwords persistent across reboots so
# they stay in sync with the Postgres volume they initialised. CI/test
# flows pass --output-dir to write straight to their runtime dir.
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "infra" / "docker" / "secrets"

SECRET_LENGTHS = {
    "DATABASE_CORE_APP_PASSWORD": 32,
    "DATABASE_CORE_INIT_PASSWORD": 32,
    "DATABASE_RESPONSE_APP_PASSWORD": 32,
    "DATABASE_RESPONSE_INIT_PASSWORD": 32,
    "FLOWFORM_APP_SECRET_KEY": 64,
}

_DB_PASSWORDS = (
    "DATABASE_CORE_APP_PASSWORD",
    "DATABASE_CORE_INIT_PASSWORD",
    "DATABASE_RESPONSE_APP_PASSWORD",
    "DATABASE_RESPONSE_INIT_PASSWORD",
)

# dev's Flask secret key and Auth0 management secret come from Secrets
# Manager (they must persist / can't be generated); test is fully
# self-contained apart from the Auth0 secret, which CI injects.
ENV_SECRETS = {
    "dev": _DB_PASSWORDS,
    "test": (*_DB_PASSWORDS, "FLOWFORM_APP_SECRET_KEY"),
}

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
        description="Generate throwaway secret files for dev/test environments."
    )
    parser.add_argument(
        "environments",
        nargs="*",
        choices=DEFAULT_ENVIRONMENTS,
        help="Which environments to generate (default: dev and test).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to write secret files into (default: {DEFAULT_OUTPUT_DIR}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    environments = tuple(dict.fromkeys(args.environments)) or DEFAULT_ENVIRONMENTS

    secrets_dir: Path = args.output_dir
    secrets_dir.mkdir(parents=True, exist_ok=True)

    created_files: list[Path] = []
    skipped_files: list[Path] = []

    for environment in environments:
        for secret_name in ENV_SECRETS[environment]:
            filepath = secrets_dir / build_filename(secret_name, environment)

            if filepath.exists():
                skipped_files.append(filepath)
                continue

            filepath.write_text(generate_secret(SECRET_LENGTHS[secret_name]) + "\n", encoding="utf-8")
            filepath.chmod(0o600)
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
