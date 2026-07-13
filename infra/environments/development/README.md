# Development environment

This directory owns development-only container configuration and local values.
Run the integrated development stack with:

```bash
docker compose -f infra/environments/development/compose/docker-compose.dev.yml up -d
```

`compose/` includes local Docker build definitions and gitignored development
environment files. The shared post-boot production-style runtime lives in
`infra/runtime`, not here.
