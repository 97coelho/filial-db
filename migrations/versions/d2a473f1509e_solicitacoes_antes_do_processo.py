"""solicitacoes antes do processo

Revision ID: d2a473f1509e
Revises: c8e941b3a126
"""
from alembic import op
import sqlalchemy as sa


revision = "d2a473f1509e"
down_revision = "c8e941b3a126"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "solicitacoes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("processo_id", sa.String(length=36), nullable=True),
        sa.Column("agente_nome", sa.String(length=180), nullable=False),
        sa.Column("cliente_nome", sa.String(length=180), nullable=False),
        sa.Column("endereco", sa.Text(), nullable=False),
        sa.Column("volume_m3", sa.Numeric(14, 3), nullable=False),
        sa.Column("data_inicial_inicio", sa.Date(), nullable=False),
        sa.Column("data_inicial_fim", sa.Date(), nullable=False),
        sa.Column("data_ofertada_inicio", sa.Date(), nullable=True),
        sa.Column("data_ofertada_fim", sa.Date(), nullable=True),
        sa.Column("data_final_inicio", sa.Date(), nullable=True),
        sa.Column("data_final_fim", sa.Date(), nullable=True),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("confirmado_por_email_em", sa.DateTime(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint("volume_m3 > 0"),
        sa.CheckConstraint("data_inicial_fim >= data_inicial_inicio"),
        sa.CheckConstraint(
            "(data_ofertada_inicio is null and data_ofertada_fim is null) or "
            "(data_ofertada_inicio is not null and data_ofertada_fim >= data_ofertada_inicio)"
        ),
        sa.CheckConstraint(
            "(data_final_inicio is null and data_final_fim is null) or "
            "(data_final_inicio is not null and data_final_fim >= data_final_inicio)"
        ),
        sa.CheckConstraint(
            "estado in ('recebida','negociacao','confirmada','convertida','cancelada')"
        ),
        sa.ForeignKeyConstraint(["processo_id"], ["processos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("solicitacoes") as batch_op:
        batch_op.create_index("ix_solicitacoes_cliente_nome", ["cliente_nome"])
        batch_op.create_index("ix_solicitacoes_estado", ["estado"])
        batch_op.create_index("ix_solicitacoes_processo_id", ["processo_id"], unique=True)


def downgrade():
    with op.batch_alter_table("solicitacoes") as batch_op:
        batch_op.drop_index("ix_solicitacoes_processo_id")
        batch_op.drop_index("ix_solicitacoes_estado")
        batch_op.drop_index("ix_solicitacoes_cliente_nome")
    op.drop_table("solicitacoes")
