# Deployment configuration

**Status: Documentation contract.**

Each environment owns an explicit configuration source and deployment procedure. Infrastructure declarations describe provisioning; application configuration describes runtime dependencies; secret stores deliver sensitive values without embedding them in Git or documentation.

For each deployed component record its service owner, deployment unit, source path, required environment variables (names only), network dependencies, health check, and rollback method.

The repository's [infrastructure files](https://github.com/Shayman-M-86/FlowForm) are the executable source. Reference exact paths after verifying the relevant deployment layout.
