from flask import Flask

from config import Config

from .extensions import db
from .models import Location
from .routes import admin_bp, inject_settings_context, main_bp


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.context_processor(inject_settings_context)

    with app.app_context():
        db.create_all()
        _seed_locations()

    return app


def _seed_locations() -> None:
    if Location.query.count() > 0:
        return

    db.session.add(
        Location(
            name="Main Warehouse",
            external_location_id="WHSE-001",
            active=True,
            is_default=True,
        )
    )
    db.session.commit()
