

from sqlalchemy import create_engine

from app.core.config import get_settings

settings = get_settings()

core_engine = create_engine(settings.pgdb_core.url)  # type: ignore
response_engine = create_engine(settings.pgdb_response.url)  # type: ignore