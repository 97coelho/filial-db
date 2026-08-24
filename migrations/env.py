from logging.config import fileConfig
from pathlib import Path
from alembic import context
from flask import current_app
from app.extensions import db

config = context.config
if config.config_file_name and Path(config.config_file_name).exists(): fileConfig(config.config_file_name)
target_metadata = db.metadata


def run_migrations_offline():
    context.configure(url=current_app.config["SQLALCHEMY_DATABASE_URI"], target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"}, render_as_batch=True)
    with context.begin_transaction(): context.run_migrations()


def run_migrations_online():
    connectable = db.engine
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True,
                          compare_type=True)
        with context.begin_transaction(): context.run_migrations()


run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
