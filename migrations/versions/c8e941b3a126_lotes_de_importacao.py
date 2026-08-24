"""lotes de importacao

Revision ID: c8e941b3a126
Revises: b7b107a6c7d8
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone
import hashlib


revision = "c8e941b3a126"
down_revision = "b7b107a6c7d8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "importacao_lotes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("origem", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("totais", sa.JSON(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("importacao_lotes") as batch_op:
        batch_op.create_index("ix_importacao_lotes_estado", ["estado"])
        batch_op.create_index("ix_importacao_lotes_fingerprint", ["fingerprint"], unique=True)

    connection = op.get_bind()
    lotes_legados = connection.execute(
        sa.text("SELECT DISTINCT lote FROM importacao_registros")
    ).scalars()
    for lote in lotes_legados:
        connection.execute(
            sa.text(
                "INSERT INTO importacao_lotes "
                "(id, fingerprint, origem, estado, totais, criado_em) "
                "VALUES (:id, :fingerprint, :origem, :estado, :totais, :criado_em)"
            ),
            {
                "id": lote,
                "fingerprint": hashlib.sha256(f"legado:{lote}".encode()).hexdigest(),
                "origem": "migração do staging anterior",
                "estado": "legado",
                "totais": "{}",
                "criado_em": datetime.now(timezone.utc),
            },
        )

    naming = {"uq": "uq_%(table_name)s_%(column_0_name)s"}
    with op.batch_alter_table(
        "importacao_registros", recreate="always", naming_convention=naming
    ) as batch_op:
        batch_op.drop_constraint("uq_importacao_registros_arquivo", type_="unique")
        batch_op.create_foreign_key(
            "fk_importacao_registros_lote",
            "importacao_lotes",
            ["lote"],
            ["id"],
        )
        batch_op.create_unique_constraint(
            "uq_importacao_registro_lote_linha",
            ["lote", "arquivo", "aba", "linha"],
        )


def downgrade():
    naming = {"uq": "uq_%(table_name)s_%(column_0_name)s"}
    with op.batch_alter_table(
        "importacao_registros", recreate="always", naming_convention=naming
    ) as batch_op:
        batch_op.drop_constraint("uq_importacao_registro_lote_linha", type_="unique")
        batch_op.drop_constraint("fk_importacao_registros_lote", type_="foreignkey")
        batch_op.create_unique_constraint(
            "uq_importacao_registros_arquivo",
            ["arquivo", "aba", "linha", "checksum"],
        )

    with op.batch_alter_table("importacao_lotes") as batch_op:
        batch_op.drop_index("ix_importacao_lotes_fingerprint")
        batch_op.drop_index("ix_importacao_lotes_estado")
    op.drop_table("importacao_lotes")
