import os
from datetime import date

from .extensions import db
from .models import AvaliacaoTemplate, Catalogo, Papel, RegraComissao, Usuario


CATALOGOS = {
    "tipo_processo": [("exportacao", "Exportação"), ("importacao", "Importação"),
                       ("domestico", "Doméstico"), ("guarda_moveis", "Guarda-móveis")],
    "unidade_medida": [("m3", "m³"), ("kg", "kg"), ("itens", "Itens")],
    "papel_organizacao": [("contratante", "Contratante"), ("agente", "Agente"),
                           ("pagadora", "Pagadora"), ("parceira", "Parceira")],
}


def seed_database():
    for nome, permissoes in [("administrador", ["*"]), ("operador", ["ler", "editar"]), ("consulta", ["ler"])]:
        if not Papel.query.filter_by(nome=nome).first(): db.session.add(Papel(nome=nome, permissoes=permissoes))
    db.session.flush()
    for grupo, values in CATALOGOS.items():
        for ordem, (codigo, nome) in enumerate(values):
            if not Catalogo.query.filter_by(grupo=grupo, codigo=codigo).first():
                db.session.add(Catalogo(grupo=grupo, codigo=codigo, nome=nome, ordem=ordem))
    if not RegraComissao.query.first():
        db.session.add(RegraComissao(versao=1, vigente_desde=date(2024, 1, 1),
            parametros={"perguntas": ["nota_1", "nota_2", "nota_3", "nota_4"], "fator": 5}))
    perguntas = [
        {"codigo": f"nota_{i}", "titulo": f"Nota {i}", "escala": [0, 10], "ordem": i}
        for i in range(1, 5)
    ]
    template = AvaliacaoTemplate.query.filter_by(nome="Avaliação padrão", versao=1).first()
    if not template:
        db.session.add(AvaliacaoTemplate(nome="Avaliação padrão", versao=1, vigente_desde=date(2024, 1, 1),
            perguntas=perguntas))
    elif template.perguntas != perguntas:
        template.perguntas = perguntas
    email = os.environ.get("ADMIN_EMAIL", "admin@local").lower()
    if not Usuario.query.filter_by(email=email).first():
        user = Usuario(email=email, nome="Administrador", papel=Papel.query.filter_by(nome="administrador").first())
        user.set_password(os.environ.get("ADMIN_PASSWORD", "admin"))
        db.session.add(user)
    db.session.commit()
