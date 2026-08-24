from datetime import date
from functools import wraps

from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (Avaliacao, AvaliacaoTemplate, Catalogo, Colaborador, Documento, Etapa,
                      Execucao, JanelaAgenda, Medida, MovimentoPool, OrdemServico,
                      Organizacao, Pessoa, Processo, RegraComissao, Usuario)
from ..services.comissoes import calcular_credito
from ..services.processos import auditar, buscar_processos, normalizar_codigo, pendencias, pode_concluir

api = Blueprint("api", __name__)


def error(message, status=400, code="invalid_request", details=None):
    return jsonify(error={"code": code, "message": message, "details": details or {}}), status


def auth_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        expected = current_app.config.get("API_TOKEN")
        bearer = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if session.get("usuario_id") or (expected and bearer == expected):
            return fn(*args, **kwargs)
        return error("Autenticação necessária", 401, "unauthorized")
    return wrapped


def iso(value): return value.isoformat() if value else None


def processo_json(p, detail=False):
    data = {"id": p.id, "codigo": p.codigo, "tipo": p.tipo, "cliente": {"id": p.cliente.id, "nome": p.cliente.nome},
            "coordenador_id": p.coordenador_id, "status_agenda": p.status_agenda,
            "status_operacao": p.status_operacao, "criado_em": iso(p.criado_em), "pendencias": pendencias(p)}
    if detail:
        data["janelas"] = [{"id": j.id, "tipo": j.tipo, "data_inicio": iso(j.data_inicio), "data_fim": iso(j.data_fim)} for j in p.janelas]
        data["medidas"] = [{"id": m.id, "tipo": m.tipo, "unidade": m.unidade, "valor": float(m.valor)} for m in p.medidas]
        data["ordens_servico"] = [{"id": o.id, "numero": o.numero, "modalidade": o.modalidade,
            "etapas": [{"id": e.id, "tipo": e.tipo, "sequencia": e.sequencia, "status": e.status, "critica": e.critica,
                "execucoes": [{"id": x.id, "data_inicio": iso(x.data_inicio), "data_fim": iso(x.data_fim),
                    "local": x.local, "equipe": [{"id": c.id, "nome": c.nome} for c in x.equipe]} for x in e.execucoes]} for e in o.etapas]} for o in p.ordens]
    return data


@api.errorhandler(IntegrityError)
def integrity_error(_):
    db.session.rollback()
    return error("O registro viola uma regra de unicidade ou relacionamento", 409, "conflict")


@api.get("/processos")
@auth_required
def processos_list():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 25, type=int), 1), 100)
    result = buscar_processos(request.args.get("q"), request.args.get("status_agenda"), request.args.get("status_operacao")).paginate(page=page, per_page=per_page)
    return jsonify(items=[processo_json(p) for p in result.items], pagination={"page": page, "per_page": per_page, "total": result.total, "pages": result.pages})


@api.post("/processos")
@auth_required
def processos_create():
    data = request.get_json(silent=True) or {}
    missing = [x for x in ("codigo", "cliente_id", "tipo") if not data.get(x)]
    if missing: return error("Campos obrigatórios ausentes", details={"fields": missing})
    if not db.session.get(Pessoa, data["cliente_id"]): return error("Cliente não encontrado", 404, "not_found")
    p = Processo(codigo=normalizar_codigo(data["codigo"]), cliente_id=data["cliente_id"], tipo=data["tipo"],
                 coordenador_id=data.get("coordenador_id"), observacoes=data.get("observacoes"))
    db.session.add(p); db.session.flush(); auditar("processo", p.id, "criacao", novo=p.codigo, usuario_id=session.get("usuario_id")); db.session.commit()
    return jsonify(processo_json(p, True)), 201


@api.get("/processos/<uuid>")
@auth_required
def processos_get(uuid):
    p = db.session.get(Processo, uuid)
    return jsonify(processo_json(p, True)) if p else error("Processo não encontrado", 404, "not_found")


@api.patch("/processos/<uuid>")
@auth_required
def processos_patch(uuid):
    p = db.session.get(Processo, uuid)
    if not p: return error("Processo não encontrado", 404, "not_found")
    data = request.get_json(silent=True) or {}
    if data.get("status_agenda") == "agendado" and not p.pode_agendar:
        return error("Para agendar, informe janela confirmada completa e estimativa em m³", 422, "business_rule")
    if data.get("status_operacao") == "concluido":
        allowed, reasons = pode_concluir(p)
        if not allowed: return error("O processo ainda possui bloqueios operacionais", 422, "business_rule", {"bloqueios": reasons})
    allowed_fields = {"codigo", "coordenador_id", "status_agenda", "status_operacao", "observacoes"}
    for field in allowed_fields & data.keys():
        old = getattr(p, field); value = normalizar_codigo(data[field]) if field == "codigo" else data[field]
        if old != value: auditar("processo", p.id, "alteracao", field, old, value, session.get("usuario_id")); setattr(p, field, value)
    db.session.commit(); return jsonify(processo_json(p, True))


@api.post("/processos/<uuid>/agenda")
@auth_required
def agenda_create(uuid):
    if not db.session.get(Processo, uuid): return error("Processo não encontrado", 404, "not_found")
    d = request.get_json(silent=True) or {}
    try: item = JanelaAgenda(processo_id=uuid, tipo=d["tipo"], data_inicio=date.fromisoformat(d["data_inicio"]), data_fim=date.fromisoformat(d["data_fim"]), observacoes=d.get("observacoes"))
    except (KeyError, ValueError): return error("tipo, data_inicio e data_fim são obrigatórios em formato ISO")
    db.session.add(item); db.session.commit(); return jsonify({"id": item.id}), 201


@api.post("/processos/<uuid>/medidas")
@auth_required
def medida_create(uuid):
    d = request.get_json(silent=True) or {}
    try: item = Medida(processo_id=uuid, tipo=d["tipo"], unidade=d["unidade"], valor=d["valor"])
    except KeyError as exc: return error(f"Campo obrigatório ausente: {exc.args[0]}")
    db.session.add(item); db.session.commit(); return jsonify({"id": item.id}), 201


@api.post("/processos/<uuid>/ordens-servico")
@auth_required
def ordem_create(uuid):
    d = request.get_json(silent=True) or {}; item = OrdemServico(processo_id=uuid, numero=d.get("numero"), modalidade=d.get("modalidade"), emissor_id=d.get("emissor_id"), observacoes=d.get("observacoes"))
    db.session.add(item); db.session.commit(); return jsonify({"id": item.id}), 201


@api.post("/ordens-servico/<uuid>/etapas")
@auth_required
def etapa_create(uuid):
    d = request.get_json(silent=True) or {}
    if not d.get("tipo"): return error("tipo é obrigatório")
    item = Etapa(ordem_servico_id=uuid, tipo=d["tipo"], sequencia=d.get("sequencia", 1), status=d.get("status", "pendente"), critica=d.get("critica", False))
    db.session.add(item); db.session.commit(); return jsonify({"id": item.id}), 201


@api.post("/etapas/<uuid>/execucoes")
@auth_required
def execucao_create(uuid):
    d = request.get_json(silent=True) or {}
    try: item = Execucao(etapa_id=uuid, data_inicio=date.fromisoformat(d["data_inicio"]), data_fim=date.fromisoformat(d["data_fim"]) if d.get("data_fim") else None, local=d.get("local"), anotacoes=d.get("anotacoes"))
    except (KeyError, ValueError): return error("data_inicio é obrigatória em formato ISO")
    item.equipe = [c for cid in d.get("colaborador_ids", []) if (c := db.session.get(Colaborador, cid))]
    db.session.add(item); db.session.commit(); return jsonify({"id": item.id}), 201


def simple_crud(model, fields):
    @auth_required
    def handler():
        if request.method == "GET":
            q = request.args.get("q", ""); query = model.query
            if q and hasattr(model, "nome"): query = query.filter(model.nome.ilike(f"%{q}%"))
            return jsonify(items=[{f: iso(getattr(x, f)) if isinstance(getattr(x, f), date) else getattr(x, f) for f in ("id", *fields)} for x in query.limit(100)])
        d = request.get_json(silent=True) or {}; item = model(**{f: d.get(f) for f in fields if f in d}); db.session.add(item); db.session.commit()
        return jsonify({"id": item.id}), 201
    return handler


for endpoint, model, fields in [("pessoas", Pessoa, ("nome", "idioma", "observacoes")), ("organizacoes", Organizacao, ("nome", "tipo", "observacoes")), ("colaboradores", Colaborador, ("nome", "telefone"))]:
    api.add_url_rule(f"/{endpoint}", endpoint, simple_crud(model, fields), methods=["GET", "POST"])


@api.get("/pendencias")
@auth_required
def pending_list():
    items = [{"processo_id": p.id, "codigo": p.codigo, "pendencias": pendencias(p)} for p in Processo.query.all()]
    return jsonify(items=[i for i in items if i["pendencias"]])


@api.get("/catalogos")
@auth_required
def catalogos_list():
    query = Catalogo.query
    if request.args.get("grupo"): query = query.filter_by(grupo=request.args["grupo"])
    if request.args.get("ativos", "true").lower() == "true": query = query.filter_by(ativo=True)
    return jsonify(items=[{"id": x.id, "grupo": x.grupo, "codigo": x.codigo, "nome": x.nome, "ativo": x.ativo} for x in query.order_by(Catalogo.grupo, Catalogo.ordem)])


@api.route("/documentos", methods=["GET", "POST"])
@auth_required
def documentos():
    if request.method == "GET":
        query = Documento.query
        if request.args.get("processo_id"): query = query.filter_by(processo_id=request.args["processo_id"])
        return jsonify(items=[{"id": x.id, "processo_id": x.processo_id, "nome": x.nome, "categoria": x.categoria,
                               "url": x.url, "caminho_relativo": x.caminho_relativo, "data_documento": iso(x.data_documento)} for x in query.limit(100)])
    d = request.get_json(silent=True) or {}
    if not d.get("nome") or not d.get("categoria"): return error("nome e categoria são obrigatórios")
    item = Documento(processo_id=d.get("processo_id"), nome=d["nome"], categoria=d["categoria"],
                     onedrive_id=d.get("onedrive_id"), url=d.get("url"), caminho_relativo=d.get("caminho_relativo"),
                     data_documento=date.fromisoformat(d["data_documento"]) if d.get("data_documento") else None,
                     descricao=d.get("descricao"))
    db.session.add(item); db.session.commit(); return jsonify({"id": item.id}), 201


@api.route("/avaliacoes", methods=["GET", "POST"])
@auth_required
def avaliacoes():
    if request.method == "GET":
        return jsonify(items=[{"id": x.id, "processo_id": x.processo_id, "template_id": x.template_id,
                               "respostas": x.respostas, "respondida_em": iso(x.respondida_em)} for x in Avaliacao.query.limit(100)])
    d = request.get_json(silent=True) or {}
    template = db.session.get(AvaliacaoTemplate, d.get("template_id"))
    if not template or not db.session.get(Processo, d.get("processo_id")): return error("Processo ou template não encontrado", 404, "not_found")
    item = Avaliacao(processo_id=d["processo_id"], template_id=d["template_id"], respostas=d.get("respostas", {}),
                     respondida_em=date.fromisoformat(d["respondida_em"]) if d.get("respondida_em") else date.today())
    db.session.add(item); db.session.flush()
    regra = RegraComissao.query.filter(RegraComissao.vigente_desde <= item.respondida_em).order_by(RegraComissao.versao.desc()).first()
    movimento = calcular_credito(item, regra) if regra else None
    db.session.commit(); return jsonify({"id": item.id, "movimento_pool_id": movimento.id if movimento else None}), 201


@api.route("/comissoes", methods=["GET"])
@auth_required
def comissoes():
    query = MovimentoPool.query
    if request.args.get("estado"): query = query.filter_by(estado=request.args["estado"])
    return jsonify(items=[{"id": x.id, "processo_id": x.processo_id, "tipo": x.tipo, "valor": float(x.valor),
                           "estado": x.estado, "criado_em": iso(x.criado_em), "estorno_de_id": x.estorno_de_id} for x in query.order_by(MovimentoPool.criado_em.desc()).limit(100)])


@api.patch("/comissoes/<uuid>")
@auth_required
def comissao_estado(uuid):
    item = db.session.get(MovimentoPool, uuid)
    if not item: return error("Movimento não encontrado", 404, "not_found")
    novo = (request.get_json(silent=True) or {}).get("estado")
    transicoes = {"calculado": {"aprovado", "cancelado"}, "aprovado": {"pago", "cancelado"}}
    if novo not in transicoes.get(item.estado, set()): return error("Transição de estado inválida", 422, "business_rule")
    item.estado = novo; db.session.commit(); return jsonify({"id": item.id, "estado": item.estado})
