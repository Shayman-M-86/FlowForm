from app.domain.errors import UserNotFoundError
from app.schema.orm.core.user import User


def ensure_user_exists(*, auth0_user_id: str, user: User | None) -> User:
    if user is None:
        raise UserNotFoundError(user_id=auth0_user_id)
    return user