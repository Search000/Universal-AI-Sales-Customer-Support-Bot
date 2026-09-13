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

    from app.api.routes.learning import learning_bp
    app.register_blueprint(learning_bp)

    from app.api.routes.facebook import facebook_bp
    app.register_blueprint(facebook_bp)

    from app.api.routes.whatsapp import whatsapp_bp
    app.register_blueprint(whatsapp_bp)

    from app.api.routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.api.routes.follow_up import follow_up_bp
    app.register_blueprint(follow_up_bp)

    from app.api.routes.onboarding import onboarding_bp
    app.register_blueprint(onboarding_bp)

    return app
