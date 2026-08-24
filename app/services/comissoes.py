from decimal import Decimal

from ..extensions import db
from ..models import Avaliacao, MovimentoPool, RegraComissao


def calcular_credito(avaliacao: Avaliacao, regra: RegraComissao) -> MovimentoPool:
    existente = MovimentoPool.query.filter_by(avaliacao_id=avaliacao.id, tipo="credito_avaliacao").first()
    if existente:
        return existente
    nomes = regra.parametros.get("perguntas", [])
    fator = Decimal(str(regra.parametros.get("fator", 5)))
    notas = [avaliacao.respostas.get(nome) for nome in nomes]
    valor = sum(Decimal(str(n)) for n in notas if n is not None) * fator
    movimento = MovimentoPool(processo_id=avaliacao.processo_id, avaliacao_id=avaliacao.id,
                              regra_id=regra.id, tipo="credito_avaliacao", valor=valor)
    db.session.add(movimento)
    return movimento
