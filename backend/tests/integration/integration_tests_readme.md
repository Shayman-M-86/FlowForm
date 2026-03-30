# Integration Test Container Setup

This integration test setup is meant for tests that need to run **inside the Docker network**, such as backend tests that connect to the test Postgres containers by service name.

## Start the test stack

Run this from the **project root**:

```bash
docker compose -f infra/docker/docker-compose.test.yml up -d --build
```

## Attach VS Code to the test container

In VS Code:

1. Open the Command Palette.
2. Run **Dev Containers: Attach to Running Container...**
3. Select the backend test container.

## Configure the container environment

Once you are inside the container:

1. Install the needed VS Code extensions in the container.
2. Sync the Python environment:

```bash
uv sync --extra dev --extra test
```

## Set the Python interpreter

VS Code should usually detect the interpreter automatically.

If it does not, manually point VS Code to the Python 3 interpreter inside the project `.venv`.

You can use this command to help find it:

```bash
uv python find
```

## Notes

- Run the Docker Compose command from the repository root.
- The integration test environment is separate from your normal host test workflow.
- This setup is mainly for tests that need access to services that are only available inside th