import re
import unicodedata
from datetime import date

from sqlalchemy import or_

from ..extensions import db
from ..models import Auditoria, Etapa, Execucao, Medida, Pessoa, Processo


def normalizar_codigo(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.strip().upper())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", "", value)


def pendencias(processo: Processo) -> list[str]:
    result = []
    if not processo.pode_agendar:
        result.append("Agenda confirmada e estimativa de m³ ainda não estão completas")
    etapas = [e for ordem in processo.ordens for e in ordem.etapas]
    if any(e.critica and e.status != "concluida" for e in etapas):
        result.append("Há etapas críticas incompletas")
    if any(not x.equipe for e in etapas for x in e.execucoes):
        result.append("Há execuções sem equipe")
    return result


def pode_concluir(processo: Processo) -> tuple[bool, list[str]]:
    bloqueios = [p for p in pendencias(processo) if "críticas" in p or "sem equipe" in p]
    return not bloqueios, bloqueios


def buscar_processos(q=None, status_agenda=None, status_operacao=None):
    query = Processo.query
    if q:
        like = f"%{q}%"
        query = query.join(Processo.cliente).filter(or_(Processo.codigo.ilike(like), Pessoa.nome.ilike(like)))
    if status_agenda:
        query = query.filter_by(status_agenda=status_agenda)
    if status_operacao:
        query = query.filter_by(status_operacao=status_operacao)
    return query.order_by(Processo.criado_em.desc())


def auditar(entidade, entidade_id, operacao, campo=None, anterior=None, novo=None, usuario_id=None, origem="api"):
    db.session.add(Auditoria(entidade=entidade, entidade_id=entidade_id, operacao=operacao,
                            campo=campo, valor_anterior=_safe(anterior), valor_novo=_safe(novo),
                            usuario_id=usuario_id, origem=origem))


def _safe(value):
    if value is None: return None
    text = str(value)
    return text[:4000]
