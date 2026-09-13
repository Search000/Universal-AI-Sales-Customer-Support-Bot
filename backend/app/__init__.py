"""
Application factory. Keeps app creation testable and modular.
"""
import logging

from flask import Flask

from app.config import config


def create_app() -> Flask:
    app = Flask(__name__)

    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from app.api.routes.health import health_bp
    app.register_blueprint(health_bp)

    from app.api.routes.test_message import test_message_bp
    app.register_blueprint(test_message_bp)

    return app
