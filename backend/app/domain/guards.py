def ensure_present[T](value: T | None, *, error: BaseException) -> T:
    if value is None:
        raise error
    return value
