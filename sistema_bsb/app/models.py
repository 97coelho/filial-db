from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    criado_em: Mapped[datetime] = mapped_column(default=now, nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(default=now, onupdate=now, nullable=False)


class Papel(db.Model):
    __tablename__ = "papeis"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(40), unique=True)
    permissoes: Mapped[list] = mapped_column(JSON, default=list)


class Usuario(db.Model, TimestampMixin):
    __tablename__ = "usuarios"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(db.String(255), unique=True, index=True)
    nome: Mapped[str] = mapped_column(db.String(160))
    senha_hash: Mapped[str] = mapped_column(db.String(255))
    ativo: Mapped[bool] = mapped_column(default=True)
    papel_id: Mapped[int] = mapped_column(db.ForeignKey("papeis.id"), index=True)
    papel: Mapped[Papel] = relationship()

    def set_password(self, password): self.senha_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.senha_hash, password)


class Catalogo(db.Model, TimestampMixin):
    __tablename__ = "catalogos"
    id: Mapped[int] = mapped_column(primary_key=True)
    grupo: Mapped[str] = mapped_column(db.String(60), index=True)
    codigo: Mapped[str] = mapped_column(db.String(60))
    nome: Mapped[str] = mapped_column(db.String(120))
    ativo: Mapped[bool] = mapped_column(default=True)
    ordem: Mapped[int] = mapped_column(default=0)
    __table_args__ = (UniqueConstraint("grupo", "codigo"),)


class Pessoa(db.Model, TimestampMixin):
    __tablename__ = "pessoas"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    nome: Mapped[str] = mapped_column(db.String(180), index=True)
    idioma: Mapped[str | None] = mapped_column(db.String(30))
    observacoes: Mapped[str | None] = mapped_column(db.Text)
    contatos: Mapped[list[Contato]] = relationship(cascade="all, delete-orphan")


class Contato(db.Model):
    __tablename__ = "contatos"
    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id: Mapped[str] = mapped_column(db.ForeignKey("pessoas.id"), index=True)
    tipo: Mapped[str] = mapped_column(db.String(20))
    valor: Mapped[str] = mapped_column(db.String(255))
    principal: Mapped[bool] = mapped_column(default=False)


class Organizacao(db.Model, TimestampMixin):
    __tablename__ = "organizacoes"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    nome: Mapped[str] = mapped_column(db.String(180), index=True)
    tipo: Mapped[str | None] = mapped_column(db.String(50))
    ativa: Mapped[bool] = mapped_column(default=True)
    observacoes: Mapped[str | None] = mapped_column(db.Text)


class Colaborador(db.Model, TimestampMixin):
    __tablename__ = "colaboradores"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    nome: Mapped[str] = mapped_column(db.String(180), index=True)
    telefone: Mapped[str | None] = mapped_column(db.String(40))
    ativo: Mapped[bool] = mapped_column(default=True)


class Processo(db.Model, TimestampMixin):
    __tablename__ = "processos"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    codigo: Mapped[str] = mapped_column(db.String(60), unique=True, index=True)
    cliente_id: Mapped[str] = mapped_column(db.ForeignKey("pessoas.id"), index=True)
    tipo: Mapped[str] = mapped_column(db.String(30), index=True)
    coordenador_id: Mapped[str | None] = mapped_column(db.ForeignKey("colaboradores.id"), index=True)
    status_agenda: Mapped[str] = mapped_column(db.String(30), default="nao_agendado", index=True)
    status_operacao: Mapped[str] = mapped_column(db.String(30), default="aberto", index=True)
    arquivado_em: Mapped[datetime | None]
    cancelado_em: Mapped[datetime | None]
    observacoes: Mapped[str | None] = mapped_column(db.Text)
    cliente: Mapped[Pessoa] = relationship(foreign_keys=[cliente_id])
    coordenador: Mapped[Colaborador | None] = relationship(foreign_keys=[coordenador_id])
    ordens: Mapped[list[OrdemServico]] = relationship(cascade="all, delete-orphan")
    janelas: Mapped[list[JanelaAgenda]] = relationship(cascade="all, delete-orphan")
    medidas: Mapped[list[Medida]] = relationship(cascade="all, delete-orphan")
    __table_args__ = (CheckConstraint("tipo in ('exportacao','importacao','domestico','guarda_moveis')"),)

    @property
    def pode_agendar(self):
        confirmadas = [j for j in self.janelas if j.tipo == "confirmada"]
        return bool(confirmadas and confirmadas[-1].data_inicio and confirmadas[-1].data_fim and
                    any(m.tipo == "estimado" and m.unidade == "m3" and m.valor is not None for m in self.medidas))


class ProcessoOrganizacao(db.Model):
    __tablename__ = "processo_organizacao"
    processo_id: Mapped[str] = mapped_column(db.ForeignKey("processos.id"), primary_key=True)
    organizacao_id: Mapped[str] = mapped_column(db.ForeignKey("organizacoes.id"), primary_key=True)
    papel: Mapped[str] = mapped_column(db.String(50), primary_key=True)


class OrdemServico(db.Model, TimestampMixin):
    __tablename__ = "ordens_servico"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    processo_id: Mapped[str] = mapped_column(db.ForeignKey("processos.id"), index=True)
    numero: Mapped[str | None] = mapped_column(db.String(80), index=True)
    emissor_id: Mapped[str | None] = mapped_column(db.ForeignKey("organizacoes.id"), index=True)
    modalidade: Mapped[str | None] = mapped_column(db.String(40))
    observacoes: Mapped[str | None] = mapped_column(db.Text)
    etapas: Mapped[list[Etapa]] = relationship(cascade="all, delete-orphan", order_by="Etapa.sequencia")


class Etapa(db.Model, TimestampMixin):
    __tablename__ = "etapas"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    ordem_servico_id: Mapped[str] = mapped_column(db.ForeignKey("ordens_servico.id"), index=True)
    tipo: Mapped[str] = mapped_column(db.String(60), index=True)
    sequencia: Mapped[int] = mapped_column(default=1)
    prevista_inicio: Mapped[date | None]
    prevista_fim: Mapped[date | None]
    status: Mapped[str] = mapped_column(db.String(30), default="pendente", index=True)
    critica: Mapped[bool] = mapped_column(default=False)
    anotacoes: Mapped[str | None] = mapped_column(db.Text)
    execucoes: Mapped[list[Execucao]] = relationship(cascade="all, delete-orphan")


execucao_colaborador = db.Table(
    "execucao_colaborador",
    db.Column("execucao_id", db.String(36), db.ForeignKey("execucoes.id"), primary_key=True),
    db.Column("colaborador_id", db.String(36), db.ForeignKey("colaboradores.id"), primary_key=True),
)


class Execucao(db.Model, TimestampMixin):
    __tablename__ = "execucoes"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    etapa_id: Mapped[str] = mapped_column(db.ForeignKey("etapas.id"), index=True)
    data_inicio: Mapped[date]
    data_fim: Mapped[date | None]
    local: Mapped[str | None] = mapped_column(db.String(240))
    anotacoes: Mapped[str | None] = mapped_column(db.Text)
    equipe: Mapped[list[Colaborador]] = relationship(secondary=execucao_colaborador)


class JanelaAgenda(db.Model, TimestampMixin):
    __tablename__ = "janelas_agenda"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    processo_id: Mapped[str] = mapped_column(db.ForeignKey("processos.id"), index=True)
    tipo: Mapped[str] = mapped_column(db.String(20))
    data_inicio: Mapped[date]
    data_fim: Mapped[date]
    observacoes: Mapped[str | None] = mapped_column(db.Text)
    __table_args__ = (CheckConstraint("data_fim >= data_inicio"),)


class Medida(db.Model, TimestampMixin):
    __tablename__ = "medidas"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    processo_id: Mapped[str] = mapped_column(db.ForeignKey("processos.id"), index=True)
    tipo: Mapped[str] = mapped_column(db.String(20))
    unidade: Mapped[str] = mapped_column(db.String(20))
    valor: Mapped[Decimal] = mapped_column(db.Numeric(14, 3))


class Local(db.Model, TimestampMixin):
    __tablename__ = "locais"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    logradouro: Mapped[str | None] = mapped_column(db.String(240))
    complemento: Mapped[str | None] = mapped_column(db.String(120))
    cidade: Mapped[str] = mapped_column(db.String(100), index=True)
    estado: Mapped[str | None] = mapped_column(db.String(60))
    pais: Mapped[str] = mapped_column(db.String(60), default="Brasil")
    cep: Mapped[str | None] = mapped_column(db.String(20))
    instrucoes: Mapped[str | None] = mapped_column(db.Text)


class ProcessoLocal(db.Model):
    __tablename__ = "processo_local"
    processo_id: Mapped[str] = mapped_column(db.ForeignKey("processos.id"), primary_key=True)
    local_id: Mapped[str] = mapped_column(db.ForeignKey("locais.id"), primary_key=True)
    papel: Mapped[str] = mapped_column(db.String(30), primary_key=True)


class Documento(db.Model, TimestampMixin):
    __tablename__ = "documentos"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    processo_id: Mapped[str | None] = mapped_column(db.ForeignKey("processos.id"), index=True)
    nome: Mapped[str] = mapped_column(db.String(255), index=True)
    categoria: Mapped[str] = mapped_column(db.String(60))
    onedrive_id: Mapped[str | None] = mapped_column(db.String(255))
    url: Mapped[str | None] = mapped_column(db.Text)
    caminho_relativo: Mapped[str | None] = mapped_column(db.Text)
    data_documento: Mapped[date | None]
    descricao: Mapped[str | None] = mapped_column(db.Text)


class AvaliacaoTemplate(db.Model, TimestampMixin):
    __tablename__ = "avaliacao_templates"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    nome: Mapped[str] = mapped_column(db.String(120))
    versao: Mapped[int]
    vigente_desde: Mapped[date]
    vigente_ate: Mapped[date | None]
    perguntas: Mapped[list] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("nome", "versao"),)


class Avaliacao(db.Model, TimestampMixin):
    __tablename__ = "avaliacoes"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    processo_id: Mapped[str] = mapped_column(db.ForeignKey("processos.id"), index=True)
    template_id: Mapped[str] = mapped_column(db.ForeignKey("avaliacao_templates.id"))
    respostas: Mapped[dict] = mapped_column(JSON)
    respondida_em: Mapped[date | None]
    template: Mapped[AvaliacaoTemplate] = relationship()
    processo: Mapped[Processo] = relationship()


class RegraComissao(db.Model, TimestampMixin):
    __tablename__ = "regras_comissao"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    versao: Mapped[int] = mapped_column(unique=True)
    vigente_desde: Mapped[date]
    vigente_ate: Mapped[date | None]
    parametros: Mapped[dict] = mapped_column(JSON)


class MovimentoPool(db.Model):
    __tablename__ = "movimentos_pool_comissoes"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    processo_id: Mapped[str | None] = mapped_column(db.ForeignKey("processos.id"), index=True)
    avaliacao_id: Mapped[str | None] = mapped_column(db.ForeignKey("avaliacoes.id"))
    regra_id: Mapped[str | None] = mapped_column(db.ForeignKey("regras_comissao.id"))
    estorno_de_id: Mapped[str | None] = mapped_column(db.ForeignKey("movimentos_pool_comissoes.id"))
    tipo: Mapped[str] = mapped_column(db.String(30))
    valor: Mapped[Decimal] = mapped_column(db.Numeric(14, 2))
    estado: Mapped[str] = mapped_column(db.String(20), default="calculado", index=True)
    justificativa: Mapped[str | None] = mapped_column(db.Text)
    criado_em: Mapped[datetime] = mapped_column(default=now)
    criado_por_id: Mapped[str | None] = mapped_column(db.ForeignKey("usuarios.id"))


class Auditoria(db.Model):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    entidade: Mapped[str] = mapped_column(db.String(80), index=True)
    entidade_id: Mapped[str] = mapped_column(db.String(36), index=True)
    campo: Mapped[str | None] = mapped_column(db.String(80))
    valor_anterior: Mapped[str | None] = mapped_column(db.Text)
    valor_novo: Mapped[str | None] = mapped_column(db.Text)
    usuario_id: Mapped[str | None] = mapped_column(db.ForeignKey("usuarios.id"))
    data: Mapped[datetime] = mapped_column(default=now, index=True)
    origem: Mapped[str] = mapped_column(db.String(30), default="web")
    operacao: Mapped[str] = mapped_column(db.String(20))


class ImportacaoRegistro(db.Model):
    __tablename__ = "importacao_registros"
    id: Mapped[int] = mapped_column(primary_key=True)
    lote: Mapped[str] = mapped_column(db.String(36), index=True)
    arquivo: Mapped[str] = mapped_column(db.Text)
    aba: Mapped[str | None] = mapped_column(db.String(160))
    linha: Mapped[int]
    checksum: Mapped[str] = mapped_column(db.String(64), index=True)
    valor_bruto: Mapped[dict] = mapped_column(JSON)
    estado: Mapped[str] = mapped_column(db.String(20), default="carregado")
    conflito: Mapped[str | None] = mapped_column(db.Text)
    __table_args__ = (UniqueConstraint("arquivo", "aba", "linha", "checksum"),)


class HistoricoProcesso(db.Model):
    __tablename__ = "historico_processos"
    id: Mapped[str] = mapped_column(db.String(36), primary_key=True, default=uid)
    codigo: Mapped[str | None] = mapped_column(db.String(60), index=True)
    cliente: Mapped[str] = mapped_column(db.String(180), index=True)
    ano: Mapped[int] = mapped_column(index=True)
    tipo: Mapped[str | None] = mapped_column(db.String(30))
    referencia_arquivo: Mapped[str] = mapped_column(db.Text)


Index("ix_etapas_prazo_status", Etapa.prevista_fim, Etapa.status)
