from datetime import date

from app.extensions import db
from app.models import (Avaliacao, AvaliacaoTemplate, Colaborador, Etapa, Execucao, JanelaAgenda,
                        Medida, OrdemServico, Pessoa, Processo, RegraComissao)
from app.services.comissoes import calcular_credito
from app.services.processos import normalizar_codigo, pode_concluir


def test_normalizacao_codigo():
    assert normalizar_codigo(" exp-14.001 ") == "EXP14001"


def test_agendamento_exige_janela_e_m3(app):
    with app.app_context():
        pessoa = Pessoa(nome="Cliente"); processo = Processo(codigo="EXP1", cliente=pessoa, tipo="exportacao")
        db.session.add(processo); db.session.flush(); assert not processo.pode_agendar
        processo.janelas.append(JanelaAgenda(tipo="confirmada", data_inicio=date(2026, 8, 20), data_fim=date(2026, 8, 21)))
        processo.medidas.append(Medida(tipo="estimado", unidade="m3", valor=10)); assert processo.pode_agendar


def test_conclusao_bloqueada_por_etapa_critica_e_equipe(app):
    with app.app_context():
        p = Processo(codigo="IMP1", cliente=Pessoa(nome="Cliente"), tipo="importacao")
        ordem = OrdemServico(numero="OS-1"); p.ordens.append(ordem)
        etapa = Etapa(tipo="entrega", critica=True); ordem.etapas.append(etapa)
        db.session.add(p); db.session.flush()
        ok, bloqueios = pode_concluir(p); assert not ok and bloqueios
        etapa.status = "concluida"; execucao = Execucao(data_inicio=date.today()); etapa.execucoes.append(execucao)
        ok, _ = pode_concluir(p); assert not ok
        execucao.equipe.append(Colaborador(nome="João")); ok, _ = pode_concluir(p); assert ok


def test_comissao_preserva_nulos_e_e_idempotente(app):
    with app.app_context():
        p = Processo(codigo="DOM1", cliente=Pessoa(nome="Cliente"), tipo="domestico")
        template = AvaliacaoTemplate(nome="Padrão", versao=1, vigente_desde=date.today(), perguntas=[])
        regra = RegraComissao(versao=1, vigente_desde=date.today(), parametros={"perguntas": ["a", "b", "c", "d"], "fator": 5})
        avaliacao = Avaliacao(processo=p, template=template, respostas={"a": 5, "b": None, "c": 4, "d": 3})
        db.session.add_all([p, template, regra, avaliacao]); db.session.flush()
        movimento = calcular_credito(avaliacao, regra); db.session.flush()
        assert movimento.valor == 60
        assert calcular_credito(avaliacao, regra).id == movimento.id


def test_api_fluxo_minimo(client, auth):
    pessoa = client.post("/api/v1/pessoas", json={"nome": "Maria"}, headers=auth)
    assert pessoa.status_code == 201
    processo = client.post("/api/v1/processos", json={"codigo": " exp-14001 ", "cliente_id": pessoa.json["id"], "tipo": "exportacao"}, headers=auth)
    assert processo.status_code == 201 and processo.json["codigo"] == "EXP14001"
    blocked = client.patch(f"/api/v1/processos/{processo.json['id']}", json={"status_agenda": "agendado"}, headers=auth)
    assert blocked.status_code == 422


def test_api_requer_autenticacao(client):
    response = client.get("/api/v1/processos")
    assert response.status_code == 401 and response.json["error"]["code"] == "unauthorized"
