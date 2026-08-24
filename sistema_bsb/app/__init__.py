import os

from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine

from .config import Config
from .extensions import db, migrate


@event.listens_for(Engine, "connect")
def sqlite_pragmas(connection, _):
    if connection.__class__.__module__.startswith("sqlite3"):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    db.init_app(app)
    migrate.init_app(app, db, directory="migrations", render_as_batch=True)

    from .api.routes import api
    from .web.routes import web
    app.register_blueprint(api, url_prefix="/api/v1")
    app.register_blueprint(web)

    @app.cli.command("seed")
    def seed():
        from .seed import seed_database
        seed_database()
        print("Cadastros iniciais criados.")

    @app.get("/health")
    def health():
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app
