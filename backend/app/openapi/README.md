# OpenAPI contract pipeline

Route decorators record metadata; Flask supplies actual paths and methods;
Pydantic supplies input and output JSON Schemas. None of these are a second
implementation of route behavior. The application still owns request parsing,
authorization, execution and response validation.

- `registry.py` records route contracts without wrapping handlers.
- `spec.py` registers schemas and dependencies, resolves Flask routes, and builds
  operations. It rejects conflicting component definitions, duplicate operations,
  unnamed exported unions, and bodies on no-content responses.
- Query models register their referenced definitions just like body models.
- Request schemas use validation mode; responses use serialization mode. Models
  with incompatible input/output aliases must use separate component names.
- Collection schemas come from Pydantic, preserving their item types and uniqueness.
- `errors.py` derives the error envelope from the runtime `ErrorPayload` typed dictionary
  owned by `api/utils/errors.py`. Stable response
  component names and supported HTTP statuses are deliberate public metadata.
- `error_examples.py` uses real HTTP exceptions and an actual current request
  validation failure. It does not instantiate business errors with guessed
  arguments or import database rule factories to fabricate examples.
- `export.py` writes deterministic YAML and supports a read-only drift check.
  Failed route discovery never replaces a previously generated document.

Do not infer constraints from property names, silently resolve schema collisions,
or skip invalid application routes to produce a superficially successful export.
The frontend generator recognizes both singular and plural response suffixes.

The exporter registers the application routes without initializing runtime
services. Generated Studio API types and permissions describe those routes.
The local node builder and its paste import use a separate schema snapshot
under `frontend/packages/schema/` during the V2 migration.
