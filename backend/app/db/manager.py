from __future__ import annotations

from flask import Flask
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.errors import InitializationError


class DatabaseManager:
    """Manages database engines and sessions for the application, supporting both core and response databases."""

    def __init__(self) -> None:
        self.core_engine: Engine | None = None
        self.response_engine: Engine | None = None
        self._core_sessionmaker: sessionmaker[Session] | None = None
        self._response_sessionmaker: sessionmaker[Session] | None = None

    def init_app(self, app: Flask) -> None:
        """Initialize the database manager with the Flask application context.

        This method sets up the database engines and sessionmakers for both
        core and response databases based on the application's settings.

        Raises:
            InitializationError: If the settings are not properly configured.
        """
        try:
            settings: Settings = app.extensions["settings"]
        except KeyError as err:
            raise InitializationError(
                "Settings must be loaded and attached to the Flask app before initializing the database manager."
            ) from err

        self.core_engine = create_engine(  # Todo - Add ability to configure settings via the config settings object.
            settings.database.core.url,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        self.response_engine = create_engine(
            settings.database.response.url,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_pre_ping=True,
            pool_recycle=1800,
        )

        self._core_sessionmaker = sessionmaker(
            bind=self.core_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )
        self._response_sessionmaker = sessionmaker(
            bind=self.response_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )

    def create_core_session(self) -> Session:
        if self._core_sessionmaker is None:
            raise RuntimeError("Core sessionmaker is not initialized.")
        return self._core_sessionmaker()

    def create_response_session(self) -> Session:
        if self._response_sessionmaker is None:
            raise RuntimeError("Response sessionmaker is not initialized.")
        return self._response_sessionmaker()

    def dispose(self) -> None:
        if self.core_engine is not None:
            self.core_engine.dispose()
        if self.response_engine is not None:
            self.response_engine.dispose()
