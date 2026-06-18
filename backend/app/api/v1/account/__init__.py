from flask import Blueprint

from app.services.users import UserService

account_bp = Blueprint("account_v1", __name__)

_users_service = UserService()

from app.api.v1.account import auth, invitations, profile  # noqa: E402
