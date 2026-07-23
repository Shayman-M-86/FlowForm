import logging

from app.logging.logging_config import configure_third_party_loggers
from app.logging.sensitive_data import protect_root_handlers


def pytest_configure():
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    configure_third_party_loggers()
    protect_root_handlers()

    # silence noisy libs
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
