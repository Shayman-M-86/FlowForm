class ApplicationError(Exception):
    """Base class for application-level errors."""
    description = "An application error occurred."


class InitializationError(Exception):
    """Error raised when the application fails to initialize correctly."""
    description = "An initialization error occurred."


class ConfigError(Exception):
    """Error raised when application configuration is invalid or missing."""
    description = "A configuration error occurred."
