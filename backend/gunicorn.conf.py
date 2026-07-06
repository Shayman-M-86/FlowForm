"""Gunicorn configuration for the FlowForm backend.

``preload_app`` is enabled so the application factory (and therefore
configuration validation) runs **once in the master process** before any
workers are forked. A catastrophic boot failure (e.g. invalid configuration)
then raises ``SystemExit`` in the master during preload and gunicorn exits
cleanly, instead of every worker crash-looping and the arbiter dumping a
``HaltServer`` traceback once all workers fail to boot.
"""

import os

# Bind / concurrency come from the environment (see backend.Dockerfile).
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:5000")
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
timeout = int(os.getenv("TIMEOUT", "60"))

# Run create_app() in the master before forking so config errors surface once
# and abort the boot cleanly instead of looping across workers.
preload_app = True


def post_fork(server, worker):  # noqa: ARG001
    """Dispose inherited DB connection pools in each freshly forked worker.

    With ``preload_app`` the application factory runs in the master, and seed
    work (``init_seed_data``) opens real database connections there. Those
    pooled connections/sockets are inherited by every forked worker; sharing a
    single connection across processes corrupts the protocol stream. Disposing
    the pools post-fork forces each worker to open its own connections lazily.
    """
    from app.core.extensions import db_manager

    db_manager.dispose()

