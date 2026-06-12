#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterable
from contextlib import suppress
from io import TextIOWrapper
from pathlib import Path
from typing import Any

if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(line_buffering=True)
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(line_buffering=True)

# ------------------------------------------------------------------------------
# Run Tests (Smart Rebuild + Persistent Test Stack)
#
# Starts the Docker test stack, runs pytest in the backend container, and keeps
# containers/volumes alive after the run. The runner fingerprints schema, build,
# and environment inputs so it can choose the smallest safe reset before a run.
#
# Usage:
#   ./run-tests.sh [--ai] [--verbose] [--logs=all|none] [--log-tail=N] [--clean-rebuild] [pytest args]
#
# Options:
#   --ai              Compact output for agents/CI: hide Compose startup chatter
#                     and omit pytest captured stdout/log sections.
#   --verbose, -v     Show full Docker/test command output and run pytest without
#                     the script's quiet defaults.
#   --logs=all        On failure, print Docker logs from all services.
#   --logs=none       On failure, skip Docker logs. This is the default.
#   --log-tail=N      Number of Docker log lines to print with --logs=all
#                     (default: 250).
#   --clean-rebuild   Force a full clean rebuild before running tests.
#   --help, -h        Print this help text.
#
# Any other arguments are passed through to pytest. If no pytest args are
# supplied, the script runs tests/.
#
# Examples:
#   ./run-tests.sh
#   ./run-tests.sh --ai -k public_link
#   ./run-tests.sh --verbose
#   ./run-tests.sh --logs=all
#   ./run-tests.sh --logs=none tests/integration
#   ./run-tests.sh --clean-rebuild --ai
#   ./run-tests.sh tests/ -k public_link
# ------------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = PROJECT_ROOT / "infra/docker/docker-compose.test.yml"
BACKEND_SERVICE = "backend-test"
CONTAINER = "flowform-backend-test"
POSTGRES_CONTAINERS = ("flowform-postgres-core-test", "flowform-postgres-response-test")
POSTGRES_VOLUMES = ("flowform_postgres_core_data", "flowform_postgres_response_data")
BACKEND_VENV_VOLUME = "flowform_backend_test_venv"
STATE_FILE = PROJECT_ROOT / ".cache/flowform-test-runner/rebuild-teardown-state.json"
FINGERPRINT_VERSION = 2

COLOR_RESET = "\033[0m"
COLOR_BLUE = "\033[34m"
COLOR_GREEN = "\033[32m"
COLOR_RED = "\033[31m"

FINGERPRINT_INPUTS = {
    "environment": (
        "infra/docker/docker-compose.test.yml",
        "infra/docker/.backend.env",
        "infra/docker/.db.core.env",
        "infra/docker/.db.response.env",
        "infra/docker/.env",
    ),
    "build": (
        "infra/docker/backend.test.Dockerfile",
        "backend/pyproject.toml",
        "backend/uv.lock",
    ),
    "schema": (
        "infra/postgres/config/pg_hba.conf",
        "infra/postgres/init/**/*",
        "backend/app/db/**/*.py",
        "backend/app/schema/orm/**/*.py",
    ),
}


class RunnerError(RuntimeError):
    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        add_help=False,
        usage="./run-tests.sh [--ai] [--verbose] [--logs=all|none] [--log-tail=N] [--clean-rebuild] [pytest args]",
    )
    parser.add_argument("--ai", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--logs", choices=("all", "none"), default="none")
    parser.add_argument("--log-tail", type=int, default=250)
    parser.add_argument("--clean-rebuild", action="store_true")
    parser.add_argument("--help", "-h", action="store_true")

    known, pytest_args = parser.parse_known_args(argv)
    if known.help:
        print_help()
        raise SystemExit(0)
    if known.log_tail < 1:
        raise RunnerError("ERROR: --log-tail must be greater than 0.")
    known.pytest_args = pytest_args or ["tests/"]
    return known


def print_help() -> None:
    script = Path(__file__).read_text(encoding="utf-8")
    in_header = False
    for line in script.splitlines():
        if line.startswith("# Run Tests"):
            in_header = True
        if in_header:
            if line.startswith("# ------") and "Examples" not in line:
                continue
            if line.startswith("# "):
                print(line[2:])
            elif line == "#":
                print()
            else:
                break


def run(args: list[str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )
    if check and completed.returncode != 0:
        command = shlex.join(args)
        output = f"\n{completed.stdout}" if capture and completed.stdout else ""
        raise RunnerError(f"ERROR: Command failed ({completed.returncode}): {command}{output}", completed.returncode)
    return completed


def compose_args(*args: str) -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE), *args]


def print_section(title: str) -> None:
    print()
    print(title)


def log_status(args: argparse.Namespace, message: str, *, ai: bool = False) -> None:
    if ai or not args.ai:
        print(message)


def supports_spinner(verbose: bool) -> bool:
    return sys.stdout.isatty() and not verbose


def tail_file(path: Path, line_count: int = 80) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-line_count:])


def finish_spinner(message: str, exit_code: int, status_column_width: int) -> None:
    if exit_code == 0:
        print(
            f"\033[2A\r\033[2K{COLOR_GREEN}✓{COLOR_RESET} "
            f"{message:<{status_column_width}} {COLOR_GREEN}Done{COLOR_RESET}"
        )
    else:
        print(
            f"\033[2A\r\033[2K{COLOR_RED}✗{COLOR_RESET} "
            f"{message:<{status_column_width}} {COLOR_RED}failed{COLOR_RESET}"
        )


def spin_until(message: str, done: Callable[[], bool], verbose: bool) -> None:
    if not supports_spinner(verbose):
        print(message)
        while not done():
            time.sleep(0.1)
        return

    spin = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    i = 0
    status_column_width = 62
    print("\n\n\n")
    while not done():
        i = (i + 1) % len(spin)
        print(f"\033[2A\r\033[2K{COLOR_BLUE}{spin[i]}{COLOR_RESET} {message:<{status_column_width}} waiting\n")
        time.sleep(0.1)


def run_with_spinner(message: str, args: list[str], verbose: bool) -> int:
    if verbose:
        print_section(message)
        return run(args, check=False).returncode

    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as step_log:
        log_path = Path(step_log.name)

    process = subprocess.Popen(
        args,
        cwd=PROJECT_ROOT,
        stdout=log_path.open("w", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        text=True,
    )
    spin_until(message, lambda: process.poll() is not None, verbose)
    exit_code = process.wait()

    if supports_spinner(verbose):
        finish_spinner(message, exit_code, 62)

    if exit_code != 0:
        print()
        print(f"ERROR: {message} failed.")
        tail = tail_file(log_path)
        if tail:
            print(tail)

    with suppress(FileNotFoundError):
        log_path.unlink()

    return exit_code


def run_callable_with_spinner(message: str, func: Callable[[], None], verbose: bool) -> int:
    if verbose:
        print_section(message)
        try:
            func()
        except RunnerError as exc:
            print(exc, file=sys.stderr)
            return exc.exit_code
        return 0

    result: queue.Queue[BaseException | None] = queue.Queue(maxsize=1)

    def target() -> None:
        try:
            func()
            result.put(None)
        except BaseException as exc:
            result.put(exc)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    spin_until(message, lambda: not result.empty(), verbose)
    thread.join()
    exc = result.get()
    exit_code = 0
    if exc is not None:
        exit_code = exc.exit_code if isinstance(exc, RunnerError) else 1

    if supports_spinner(verbose):
        finish_spinner(message, exit_code, 62)

    if exc is not None:
        print()
        print(f"ERROR: {message} failed.")
        print(str(exc), file=sys.stderr)

    return exit_code


def ensure_docker_running() -> None:
    if run(["docker", "info"], check=False, capture=True).returncode == 0:
        return

    if not os.environ.get("WSL_DISTRO_NAME") and not os.environ.get("WSL_INTEROP"):
        raise RunnerError("Docker daemon is not reachable. Start Docker and re-run.")

    docker_desktop_exe = Path("/mnt/c/Program Files/Docker/Docker/Docker Desktop.exe")
    if not docker_desktop_exe.exists():
        raise RunnerError(
            "Docker Desktop not found at expected path:\n"
            f"  {docker_desktop_exe}\n"
            "Start Docker Desktop manually and re-run."
        )

    print("Docker daemon not running - launching Docker Desktop")
    docker_desktop_win = run(["wslpath", "-w", str(docker_desktop_exe)], capture=True).stdout.strip()
    run(["cmd.exe", "/c", "start", "", docker_desktop_win], check=False, capture=True)

    wait_seconds = 120
    elapsed = 0
    while run(["docker", "info"], check=False, capture=True).returncode != 0:
        if elapsed >= wait_seconds:
            raise RunnerError(f"Timed out after {wait_seconds}s waiting for Docker Desktop to start.")
        time.sleep(2)
        elapsed += 2
    print(f"Docker is ready ({elapsed}s)")


def iter_fingerprint_files(patterns: Iterable[str]) -> Iterable[Path]:
    seen: set[Path] = set()
    for pattern in patterns:
        matches = sorted(PROJECT_ROOT.glob(pattern))
        for path in matches:
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            yield path


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_bucket_fingerprint(patterns: Iterable[str]) -> dict[str, Any]:
    files = {str(path.relative_to(PROJECT_ROOT)): file_hash(path) for path in iter_fingerprint_files(patterns)}
    digest = hashlib.sha256()
    for name, checksum in sorted(files.items()):
        digest.update(f"{name}\0{checksum}\n".encode())
    return {
        "digest": digest.hexdigest(),
        "files": files,
    }


def current_fingerprint() -> dict[str, Any]:
    buckets = {bucket: build_bucket_fingerprint(patterns) for bucket, patterns in sorted(FINGERPRINT_INPUTS.items())}
    digest = hashlib.sha256()
    digest.update(f"v{FINGERPRINT_VERSION}\n".encode())
    for bucket, fingerprint in sorted(buckets.items()):
        digest.update(f"{bucket}\0{fingerprint['digest']}\n".encode())
    return {
        "version": FINGERPRINT_VERSION,
        "digest": digest.hexdigest(),
        "buckets": buckets,
    }


def load_previous_fingerprint() -> dict[str, Any] | None:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def save_fingerprint(fingerprint: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(fingerprint, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def changed_files(previous_bucket: dict[str, Any] | None, current_bucket: dict[str, Any]) -> list[str]:
    if previous_bucket is None:
        return []
    previous_files = previous_bucket.get("files", {})
    current_files = current_bucket.get("files", {})
    paths = sorted(set(previous_files) | set(current_files))
    return [path for path in paths if previous_files.get(path) != current_files.get(path)]


def changed_buckets(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, list[str]]:
    if previous is None or previous.get("version") != current.get("version"):
        return {}

    previous_buckets = previous.get("buckets", {})
    current_buckets = current.get("buckets", {})
    changed: dict[str, list[str]] = {}
    for bucket in sorted(set(previous_buckets) | set(current_buckets)):
        previous_bucket = previous_buckets.get(bucket)
        current_bucket = current_buckets.get(bucket)
        if previous_bucket is None or current_bucket is None:
            changed[bucket] = []
            continue
        if previous_bucket.get("digest") != current_bucket.get("digest"):
            changed[bucket] = changed_files(previous_bucket, current_bucket)
    return changed


def docker_stack_exists() -> bool:
    completed = run(compose_args("ps", "-a", "-q"), check=False, capture=True)
    return bool(completed.stdout.strip())


def compose_volume_names(volume: str) -> list[str]:
    completed = run(
        [
            "docker",
            "volume",
            "ls",
            "-q",
            "--filter",
            f"label=com.docker.compose.volume={volume}",
        ],
        capture=True,
    )
    names = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if names:
        return names

    fallback = run(["docker", "volume", "ls", "-q", "--filter", f"name={volume}"], capture=True)
    return [line.strip() for line in fallback.stdout.splitlines() if line.strip()]


def docker_volumes_exist() -> bool:
    return any(compose_volume_names(volume) for volume in (*POSTGRES_VOLUMES, BACKEND_VENV_VOLUME))


def remove_compose_volumes(volumes: Iterable[str], verbose: bool) -> None:
    names = []
    for volume in volumes:
        names.extend(compose_volume_names(volume))

    if not names:
        return

    if run_with_spinner("Removing stale test volumes", ["docker", "volume", "rm", *sorted(set(names))], verbose) != 0:
        raise RunnerError("Failed to remove stale test volumes.")


def container_state(container: str) -> str:
    return run(
        ["docker", "inspect", "-f", "{{.State.Status}}", container],
        check=False,
        capture=True,
    ).stdout.strip()


def container_health(container: str) -> str:
    return run(
        ["docker", "inspect", "-f", "{{if .State.Health}}{{.State.Health.Status}}{{end}}", container],
        check=False,
        capture=True,
    ).stdout.strip()


def test_stack_is_ready() -> bool:
    if container_state(CONTAINER) != "running":
        return False

    for postgres_container in POSTGRES_CONTAINERS:
        if container_state(postgres_container) != "running":
            return False
        if container_health(postgres_container) != "healthy":
            return False

    return True


def wait_for_backend() -> None:
    wait_timeout = 120
    wait_elapsed = 0

    while True:
        status = container_state(CONTAINER)
        if status == "running":
            return
        if status in {"exited", "dead"}:
            raise RunnerError(f"Container '{CONTAINER}' entered terminal state '{status}'.")
        if wait_elapsed >= wait_timeout:
            current_state = status or "unknown"
            raise RunnerError(
                f"Timed out after {wait_timeout}s waiting for '{CONTAINER}'.\nCurrent state: '{current_state}'"
            )

        time.sleep(1)
        wait_elapsed += 1


def dump_logs(log_mode: str, log_tail: int) -> None:
    if log_mode == "none":
        return

    print_section(f"Docker logs from all services, last {log_tail} lines")
    run(compose_args("logs", "--no-color", f"--tail={log_tail}"), check=False)


def print_changed_bucket_preview(changed: dict[str, list[str]]) -> None:
    for bucket, paths in changed.items():
        print(f"    {bucket}: changed")
        preview = paths[:6]
        for path in preview:
            print(f"      - {path}")
        if len(paths) > len(preview):
            print(f"      ...and {len(paths) - len(preview)} more")


def explain_fingerprint_decision(
    args: argparse.Namespace,
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    stack_exists: bool,
) -> tuple[bool, bool, bool]:
    if args.clean_rebuild:
        print("Full clean rebuild requested.")
        return True, False, False

    if previous is None:
        if stack_exists or docker_volumes_exist():
            print("No saved fingerprint for the existing test stack; rebuilding clean environment.")
            return True, False, False
        log_status(args, "No existing test stack detected; starting fresh environment.")
        return False, False, False

    if previous.get("version") != current.get("version"):
        print("Test runner fingerprint version changed; rebuilding clean environment.")
        return True, False, False

    if previous.get("digest") != current.get("digest"):
        changed = changed_buckets(previous, current)
        print("Test environment inputs changed.")
        if changed:
            print_changed_bucket_preview(changed)

        if "environment" in changed:
            print("Environment/compose inputs changed; rebuilding clean environment.")
            return True, False, False

        rebuild_backend = "build" in changed
        reset_db = "schema" in changed
        if rebuild_backend:
            print("Build inputs changed; backend image and venv will be refreshed.")
        if reset_db:
            print("Schema inputs changed; Postgres test volumes will be reset.")
        return False, rebuild_backend, reset_db

    log_status(args, "Test environment fingerprint unchanged; reusing existing test environment.")
    return False, False, False


def start_environment(args: argparse.Namespace) -> bool:
    current = current_fingerprint()
    previous = load_previous_fingerprint()
    stack_exists = docker_stack_exists()
    full_clean, rebuild_backend, reset_db = explain_fingerprint_decision(
        args,
        previous,
        current,
        stack_exists,
    )

    if not full_clean and not rebuild_backend and not reset_db and test_stack_is_ready():
        log_status(args, "Test environment already running and healthy; skipping Compose startup.")
        save_fingerprint(current)
        return True

    if full_clean:
        cleanup_exit = run_with_spinner(
            "Cleaning test environment",
            compose_args("down", "-v", "--remove-orphans"),
            args.verbose,
        )
        if cleanup_exit != 0:
            raise RunnerError("Failed to clean changed test environment.")
        if run_with_spinner("Building test images", compose_args("build"), args.verbose) != 0:
            raise RunnerError("Failed to build test images.")
        up_args = compose_args("up", "-d", "--no-build", "--quiet-pull", BACKEND_SERVICE)
    else:
        stop_changed_environment = rebuild_backend or reset_db
        if (
            stop_changed_environment
            and run_with_spinner(
                "Stopping changed test environment",
                compose_args("down", "--remove-orphans"),
                args.verbose,
            )
            != 0
        ):
            raise RunnerError("Failed to stop changed test environment.")

        if reset_db:
            remove_compose_volumes(POSTGRES_VOLUMES, args.verbose)

        if rebuild_backend:
            remove_compose_volumes((BACKEND_VENV_VOLUME,), args.verbose)
            if run_with_spinner("Building test images", compose_args("build"), args.verbose) != 0:
                raise RunnerError("Failed to build test images.")
            up_args = compose_args("up", "-d", "--no-build", "--quiet-pull", BACKEND_SERVICE)
        else:
            up_args = compose_args("up", "-d", "--quiet-pull", BACKEND_SERVICE)

    if args.verbose:
        print_section("Starting test environment")
        exit_code = run(up_args, check=False).returncode
    elif args.ai:
        exit_code = run_with_spinner("Starting test environment", up_args, args.verbose)
    else:
        print_section("Starting test environment")
        exit_code = run(up_args, check=False).returncode

    if exit_code != 0:
        if not full_clean:
            print("Reuse start failed; rebuilding test images and retrying once.")
            if run_with_spinner("Building test images", compose_args("build"), args.verbose) != 0:
                raise RunnerError("Failed to build test images.")
            retry_args = compose_args("up", "-d", "--no-build", "--quiet-pull", BACKEND_SERVICE)
            if run_with_spinner("Starting rebuilt test environment", retry_args, args.verbose) != 0:
                raise RunnerError("Failed to start rebuilt test environment.")
        else:
            raise RunnerError("Failed to start test environment.")

    save_fingerprint(current)
    return False


def pytest_output_mode(args: argparse.Namespace) -> list[str]:
    if args.verbose:
        return []

    output_mode = ["-q", "--tb=short"]
    if args.ai:
        output_mode.extend(["--show-capture=no", "--color=no"])
    return output_mode


def run_tests(args: argparse.Namespace) -> int:
    output_mode = pytest_output_mode(args)
    pytest_command = ["uv", "run", "pytest", *output_mode, *args.pytest_args]

    if not args.ai:
        print_section("Running tests")
        print(shlex.join(pytest_command))

    docker_exec = ["docker", "exec"]
    if sys.stdin.isatty() and sys.stdout.isatty():
        docker_exec.append("-it")
    docker_exec.extend([CONTAINER, *pytest_command])

    return run(docker_exec, check=False).returncode


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    ensure_docker_running()

    try:
        already_ready = start_environment(args)
        if not already_ready:
            wait_exit = run_callable_with_spinner("Waiting for backend-test container", wait_for_backend, args.verbose)
            if wait_exit != 0:
                dump_logs(args.logs, args.log_tail)
                return wait_exit

        test_exit = run_tests(args)
        if test_exit != 0:
            if test_exit == 5:
                print("No tests matched the requested pytest selection.")
                return test_exit
            print_section("Tests failed")
            dump_logs(args.logs, args.log_tail)
            return test_exit

        if not args.ai:
            print_section("Tests passed")
            print("Test environment kept running for the next run.")
        return 0
    except RunnerError as exc:
        print(str(exc), file=sys.stderr)
        dump_logs(args.logs, args.log_tail)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
