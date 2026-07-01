from flask import Blueprint

from app.services.account import UserAccountService
from app.services.members import MembersService
from app.services.users import UserService

account_bp = Blueprint("account_v1", __name__)

_users_service = UserService()
account_service = UserAccountService()
members_service = MembersService()

from app.api.v1.account import auth, invitations, profile  # noqa: E402
