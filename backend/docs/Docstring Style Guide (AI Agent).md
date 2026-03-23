
# FlowForm — Python Docstring Style Guide (AI Agent)

## Purpose

This guide defines how all functions must be documented.

The goal is:

- consistent documentation
- easy readability
- minimal noise
- alignment with backend/API development

* * *

## Core Rules

1. Always use **type hints**
2. Always include a **docstring unless the function is trivial**
3. Use **Google-style docstrings**
4. Keep descriptions **short and clear**
5. Do not repeat type information already in annotations
6. Do not describe obvious behavior

* * *

## Standard Structure

Every non-trivial function must follow this structure:

    """Short one-line description. Args: param: Description. Returns: Description of return value."""

* * *

## Function Categories

### 1. Simple Helper Functions

Use a single-line docstring.

    """Return the client IP address."""

* * *

### 2. Standard Functions

Use Args + Returns.

    """Create a new form. Args: title: The form title. user_id: ID of the creator. Returns: The created Form instance."""

* * *

### 3. Complex Functions

Include Raises when relevant.

    """Process a form submission. Args: form_id: The form identifier. answers: Submitted answers. Returns: The processed submission result. Raises: ValueError: If answers are invalid."""

* * *

### 4. Flask API Routes

Focus on request/response behavior.

    """Create a new form. Expects: JSON body with: - title: The form title. Returns: JSON response containing the created form. Raises: 400: If required fields are missing. 401: If user is not authenticated."""

* * *

### 5. Middleware Functions

Only describe purpose and arguments.

    """Register request logging hooks. Args: app: Flask application instance. include_duration: Whether to log request timing."""

* * *

### 6. Audit / Security Functions

Clearly describe the event meaning.

    """Record an audit event for a user action. Args: event_type: Type of event (e.g. "form.created"). user_id: ID of the acting user. resource_type: Type of resource affected. resource_id: Identifier of the resource."""

* * *

## Optional Sections

Only include these when useful:

### Raises

Use when errors are meaningful to callers.

    Raises: ValueError: If input is invalid.

### Notes

Use for important behavior details.

    Notes: Does not commit the database session.

### Example (mainly for APIs)

    Example: POST /api/v1/forms { "title": "Survey" }

* * *

## What to Avoid

Do NOT:

- repeat type hints
- write long paragraphs
- describe obvious behavior
- include implementation details

Bad example:

    """This function takes a title and creates a form object and saves it."""

* * *

## Length Guidelines

- Simple function → 1 line
- Normal function → 3–8 lines
- Complex function → up to 12 lines max

* * *

## Naming Consistency

- Use clear parameter names
- Keep descriptions aligned with names
- Use consistent terminology:

  - "form"
  - "submission"
  - "rule"
  - "user"

* * *

## Tone and Style

- Direct and neutral
- No filler words
- No corporate language
- No unnecessary explanation

Good:

    Create a new form.

Bad:

    This function is responsible for creating a form within the system.

* * *

## Final Rule

If the function is easy to understand from its name and type hints, keep the docstring minimal.

If the function requires thought to understand, document it clearly.
