
class ApplicationError(Exception):
    description = "An application error occurred."

class InitializationError(Exception):
    description = "An initialization error occurred."

class ConfigError(Exception):
    description = "A configuration error occurred."

