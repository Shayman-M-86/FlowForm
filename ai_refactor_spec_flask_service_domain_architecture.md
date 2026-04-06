# AI Refactor Specification

## Goal

Refactor existing Flask routes into a consistent structure.

The refactor should stay simple.

The agent should focus on moving logic into the correct layer, not redesigning the whole application.

Each refactor has to be done route-by-route and must be approved before moving on to the next.&#x20;

---

## Core refactor rules

For each existing route:

1. Identify the route’s real purpose.
2. Break apart the work currently being done in the route.
3. Move use-case and workflow logic into a service.
4. Move reusable query/data-access logic into a repository where appropriate.
5. Move rule checks and failure conditions into domain functions.
6. Keep the route thin.

---

## Target structure

### Route

Route code should only do the following:

- receive the HTTP request
- parse and validate the request with the existing Pydantic request schema/helper
- get the correct database session
- call one service entrypoint
- serialize and return the success response

Routes should not contain business-rule branching or deep workflow logic.

### Service

Service code should:

- coordinate the use case
- call repositories or perform DB work
- call domain functions for rule checks
- return plain result data

Service code should not handle HTTP response formatting.

### Repository

Repository code should contain:

- reusable query logic
- reusable persistence helpers
- data-access operations that are repeated or clearly belong outside the service

Repositories should not contain business-rule decisions.

### Domain

Domain code should contain:

- business rules
- validity checks
- state checks
- failure-condition checks

Domain functions should raise the existing custom application/domain errors.

Expected failures should be raised from domain logic, not manually formatted in routes.

---

## Important implementation rule

Services should not manually build error responses.

Routes should not manually build expected error responses.

Expected failure checks should be moved into domain functions that raise the existing custom errors.

The centralized error-handling layer already exists and should be relied on.

---

## Refactor procedure

For each route, the agent must do this in order:

### 1. Determine the route purpose

Identify what the route is actually doing.

Examples:

- resolving a public link
- creating a survey
- publishing a survey
- submitting a response
- listing a resource

### 2. Identify everything currently happening in the route

Look for:

- request parsing
- database selection
- queries
- branching logic
- business rules
- error handling
- response building

### 3. Keep only route-level concerns in the route

The final route should normally look like:

```python
@bp.route("/example", methods=["POST"])
def example_route():
    payload = parse_request(SomeRequestSchema, request.get_json(silent=True))
    db = get_correct_db()
    result = some_service.do_use_case(db, payload=payload)
    return SomeResponseSchema.model_validate(result).model_dump(mode="json"), 200
```

### 4. Move workflow into a service

If the route is doing multiple steps, those steps belong in a service.

Examples of service-level logic:

- load entity A
- verify entity B exists
- check whether an action is allowed
- load related records
- perform the operation
- return result data

### 5. Move rule checks into domain functions

If the code is checking whether something is missing, inactive, expired, unpublished, forbidden, invalid, or otherwise not allowed, that check should usually become a domain function.

Example:

```python
def ensure_is_active(*, link: SurveyPublicLink) -> None:
    if not link.is_active:
        raise LinkInactiveError()
```

### 6. Move reusable query logic into repositories where appropriate

If query logic is repeated or clearly represents data access, move it into a repository.

Example:

```python
def resolve_token(db: Session, token: str) -> SurveyPublicLink | None:
    ...
```

### 7. Return plain result data from the service

Service methods should return plain result objects or ORM/domain data needed by the route.

The route should build the final response schema.

---

## Strict rules

### Routes must not

- contain business-rule branching
- contain repeated expected-error response formatting
- perform deep use-case orchestration
- manually decide many failure states inline

### Services must not

- return Flask responses
- call `jsonify`
- manually format expected error JSON
- act like routes

### Repositories must not

- contain business rules
- contain HTTP concerns

### Domain functions must

- perform rule checks
- raise the existing custom errors for expected failures

---

## The main pattern

The refactor target is:

- route parses request
- route gets DB
- route calls service
- service performs workflow
- service uses repositories for data access where useful
- service uses domain functions for rule checks
- domain functions raise expected errors
- route serializes success result

---

## Example: before and after

### Before

```python
@public_bp.route("/links/resolve", methods=["POST"])
def resolve_link():
    db = get_core_db()
    data: ResolveTokenRequest = parse(ResolveTokenRequest, request)

    link = link_svc.resolve_token(db, data.token)
    if link is None:
        return ErrorResponse.return_it("Invalid or unknown token", "NOT_FOUND", status_code=404)
    if not link.is_active:
        return ErrorResponse.return_it("This link is inactive", "LINK_INACTIVE", status_code=403)

    survey = survey_svc.get_survey(db, link.survey.project_id, link.survey_id)
    published_version = None
    if survey and survey.published_version_id is not None:
        published_version = db.scalar(select(SurveyVersion).where(SurveyVersion.id == survey.published_version_id))

    return SuccessResponse.return_it(...)
```

### After

```python
@public_bp.route("/links/resolve", methods=["POST"])
def resolve_link():
    payload = parse(ResolveTokenRequest, request)

    core_db = get_core_db()

    result = public_link_service.resolve_link(core_db,payload=payload)
    response = ResolveLinkOut(
        link=PublicLinkOut.model_validate(result.link),
        survey=SurveyOut.model_validate(result.survey),
        published_version=SurveyVersionOut.model_validate(result.published_version),
    )

    return response.model_dump(mode="json"), 200
```

Service:

```python
@dataclass(slots=True)
class ResolveLinkResult:
    """Result of resolving a public link token."""
    link: SurveyPublicLink
    survey: Survey
    published_version: SurveyVersion

class PublicLinkService:
    def resolve_link(self, db: Session, *, payload: ResolveTokenRequest) -> ResolveLinkResult:
        link = public_link_rules.ensure_is_not_none(
            link=public_link_repo.resolve_token(db, payload.token)
        )
        public_link_rules.ensure_is_active(link=link)
        public_link_rules.ensure_not_expired(link=link)

        survey = survey_rules.ensure_not_none(
            survey=surveys_repo.get_survey(db, project_id=link.survey.project_id, survey_id=link.survey_id),
            survey_id=link.survey_id,
            project_id=link.survey.project_id,
        )

        published_version = survey_rules.ensure_is_published(
            survey_version=surveys_repo.get_published_version(db, survey),
            survey_id=link.survey_id,
            project_id=link.survey.project_id,
        )

        return ResolveLinkResult(
            link=link,
            survey=survey,
            published_version=published_version,
        )
```

Domain:

```python
def ensure_is_not_none(*, link: SurveyPublicLink | None) -> SurveyPublicLink:
    if link is None:
        raise LinkNotFoundError()
    return link


def ensure_is_active(*, link: SurveyPublicLink) -> None:
    if not link.is_active:
        raise LinkInactiveError()
```

Repository:

```python
def resolve_token(db: Session, token: str) -> SurveyPublicLink | None:
    if len(token) < 8:
        return None

    prefix = token[:8]
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    return db.scalar(
        select(SurveyPublicLink).where(
            SurveyPublicLink.token_prefix == prefix,
            SurveyPublicLink.token_hash == token_hash,
        )
    )
```

---

## Final instruction to the agent

Refactor route-by-route.

For each route:

- identify its purpose
- strip it down to API-boundary work only
- move workflow into a service
- move reusable data-access logic into repositories where appropriate
- move rule checks and expected failure checks into domain functions
- keep success serialization in the route
- rely on the existing centralized error-handling layer

Do not overengineer. Do not redesign unrelated parts of the codebase. Do not introduce unnecessary abstractions. Preserve behavior while aligning the structure with these rules. 



Remember: complete the refactor, present the refactor to me, and await approval for the next route.&#x20;

