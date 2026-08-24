import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import Papel, Usuario


class Config(TestConfig):
    API_TOKEN = "test-token"


@pytest.fixture
def app():
    app = create_app(Config)
    with app.app_context():
        db.create_all()
        papel = Papel(nome="administrador", permissoes=["*"])
        user = Usuario(email="admin@teste", nome="Admin", papel=papel); user.set_password("segredo")
        db.session.add_all([papel, user]); db.session.commit()
        yield app
        db.session.remove(); db.drop_all()


@pytest.fixture
def client(app): return app.test_client()


@pytest.fixture
def auth(): return {"Authorization": "Bearer test-token"}
