from app.extensions import db
from app.models import Pessoa, Processo


def login(client):
    return client.post("/login", data={"email": "admin@teste", "senha": "segredo"})


def test_csv_excel_pt_br(app, client):
    with app.app_context():
        db.session.add(Processo(codigo="EXP1", cliente=Pessoa(nome="José Ávila"), tipo="exportacao")); db.session.commit()
    login(client); response = client.get("/exportar/processos.csv")
    assert response.status_code == 200 and response.data.startswith(b"\xef\xbb\xbf") and b";" in response.data


def test_xlsx_tem_filtro_e_tipos(app, client):
    with app.app_context():
        db.session.add(Processo(codigo="IMP1", cliente=Pessoa(nome="Ana"), tipo="importacao")); db.session.commit()
    login(client); response = client.get("/exportar/processos.xlsx")
    assert response.status_code == 200 and response.data[:2] == b"PK"
