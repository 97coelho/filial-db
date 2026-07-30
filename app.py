"""
app.py
------
Web app local (Flask) para inserir novos dados no banco `mudancas_filial.db`
sem precisar escrever SQL manualmente ou digitar linha a linha no DB Browser.

Rotas disponíveis:
  /                 -> painel inicial (contagens por tabela + processos recentes)
  /agenda/novo       -> formulário para abrir uma nova Agenda (nasce o processo)
  /cliente/novo      -> formulário para vincular um Cliente a um processo existente
  /servico/novo      -> formulário para registrar um Servico de um processo existente
  /avaliacao/novo    -> formulário para lançar uma Avaliacao de um processo existente

Como rodar localmente (sem Docker), a partir da pasta do projeto:
    pip install flask
    python3 app.py

Depois é só abrir http://localhost:5000 no navegador.
Para rodar via Docker, veja as instruções de docker-compose.yml enviadas junto.
"""

import sqlite3
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
# Necessário para o Flask conseguir usar flash() (mensagens de sucesso/erro).
# Como este é um app local, de uso interno, uma chave fixa é suficiente.
app.secret_key = "chave-local-mudancas-filial"

# O banco fica sempre na mesma pasta deste arquivo (app.py).
CAMINHO_DB = Path(__file__).parent / "mudancas_filial.db"


def conectar() -> sqlite3.Connection:
    """Abre uma conexão nova com o banco, com FKs ativadas e
    permitindo acessar colunas pelo nome (ex: linha['processo'])."""
    conexao = sqlite3.connect(CAMINHO_DB)
    conexao.execute("PRAGMA foreign_keys = ON;")
    conexao.row_factory = sqlite3.Row
    return conexao


def listar_processos():
    """Lista os processos já existentes em Agenda, usada para popular os
    <select> dos formulários de Cliente, Servico e Avaliacao — assim o
    usuário nunca digita o código do processo à mão nessas telas, só
    escolhe de uma lista (evita erro de digitação e viola menos a
    integridade referencial)."""
    conexao = conectar()
    processos = conexao.execute(
        "SELECT processo, origem, destino FROM Agenda ORDER BY processo DESC"
    ).fetchall()
    conexao.close()
    return processos


@app.route("/")
def index():
    """Painel inicial: mostra quantos registros existem em cada tabela
    e os 5 processos mais recentes, com atalhos para os formulários."""
    conexao = conectar()
    contagens = {
        "Agenda": conexao.execute("SELECT COUNT(*) FROM Agenda").fetchone()[0],
        "Clientes": conexao.execute("SELECT COUNT(*) FROM Clientes").fetchone()[0],
        "Servicos": conexao.execute("SELECT COUNT(*) FROM Servicos").fetchone()[0],
        "Avaliacoes": conexao.execute("SELECT COUNT(*) FROM Avaliacoes_Brutas").fetchone()[0],
    }
    ultimos_processos = conexao.execute(
        """
        SELECT processo, origem, destino, status_agenda
        FROM Agenda
        ORDER BY rowid DESC
        LIMIT 5
        """
    ).fetchall()
    conexao.close()
    return render_template(
        "index.html", contagens=contagens, ultimos_processos=ultimos_processos
    )


# ---------------------------------------------------------------------
# Agenda — aqui nasce o processo
# ---------------------------------------------------------------------
@app.route("/agenda/novo", methods=["GET", "POST"])
def agenda_novo():
    if request.method == "POST":
        # request.form.get(campo) or None: se o campo veio vazio do
        # formulário HTML, guardamos NULL no banco em vez de string vazia.
        dados = (
            request.form["processo"].strip(),
            request.form.get("recebido_em") or None,
            request.form.get("data_a_inicial") or None,
            request.form.get("data_b_inicial") or None,
            request.form.get("data_a_ofertada") or None,
            request.form.get("data_b_ofertada") or None,
            request.form.get("volume") or None,
            request.form.get("engradados") or None,
            request.form.get("caixas") or None,
            request.form.get("lifts") or None,
            request.form.get("tipo") or None,
            request.form.get("status_agenda") or None,
            request.form.get("origem") or None,
            request.form.get("destino") or None,
            request.form.get("anotacoes_agenda") or None,
        )
        conexao = conectar()
        try:
            conexao.execute(
                """
                INSERT INTO Agenda (
                    processo, recebido_em, data_a_inicial, data_b_inicial,
                    data_a_ofertada, data_b_ofertada, volume, engradados,
                    caixas, lifts, tipo, status_agenda, origem, destino,
                    anotacoes_agenda
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                dados,
            )
            conexao.commit()
            flash(f"Processo '{dados[0]}' criado com sucesso!", "success")
            return redirect(url_for("index"))
        except sqlite3.IntegrityError:
            # processo é TEXT PRIMARY KEY: já existe um igual
            flash(
                f"Já existe um processo com o código '{dados[0]}'. "
                "Escolha um código diferente.",
                "danger",
            )
        finally:
            conexao.close()
    return render_template("agenda_form.html")


# ---------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------
@app.route("/cliente/novo", methods=["GET", "POST"])
def cliente_novo():
    if request.method == "POST":
        dados = (
            request.form["processo"],
            request.form["nome_cliente"].strip(),
            request.form.get("email") or None,
            request.form.get("email_agendor") or None,
            request.form.get("agente") or None,
            request.form.get("empresa") or None,
        )
        conexao = conectar()
        try:
            conexao.execute(
                """
                INSERT INTO Clientes (
                    processo, nome_cliente, email, email_agendor, agente, empresa
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                dados,
            )
            conexao.commit()
            flash(f"Cliente '{dados[1]}' vinculado ao processo {dados[0]}.", "success")
            return redirect(url_for("index"))
        except sqlite3.IntegrityError as erro:
            flash(f"Erro ao salvar cliente: {erro}", "danger")
        finally:
            conexao.close()
    return render_template("cliente_form.html", processos=listar_processos())


# ---------------------------------------------------------------------
# Servicos
# ---------------------------------------------------------------------
# Lista de todos os campos da tabela Servicos, na mesma ordem do schema.
# Mantendo essa lista centralizada, o INSERT é montado dinamicamente
# em vez de repetir os 34 campos manualmente na query.
CAMPOS_SERVICO = [
    "processo", "servicos", "modal", "os", "ref_externa", "cidade",
    "data_inicio", "data_final", "m3_real", "quant_itens", "peso_kg",
    "peso_bruto", "peso_bruto_real_1", "peso_liquido", "peso_liquido_real_1",
    "etd", "eta", "liftvan", "peso_liftvan", "tara_liftvan", "icamento",
    "container_20", "container_40", "quant_container_20", "quant_cont_40",
    "contents", "empresa", "tipo_cliente", "status_servico",
    "faturamento", "fatura", "coordenadora", "anotacoes_servico",
]


@app.route("/servico/novo", methods=["GET", "POST"])
def servico_novo():
    if request.method == "POST":
        valores = [request.form.get(campo) or None for campo in CAMPOS_SERVICO]
        colunas = ", ".join(CAMPOS_SERVICO)
        placeholders = ", ".join("?" for _ in CAMPOS_SERVICO)
        conexao = conectar()
        try:
            conexao.execute(
                f"INSERT INTO Servicos ({colunas}) VALUES ({placeholders})",
                valores,
            )
            conexao.commit()
            flash("Serviço registrado com sucesso!", "success")
            return redirect(url_for("index"))
        except sqlite3.IntegrityError as erro:
            flash(f"Erro ao salvar serviço: {erro}", "danger")
        finally:
            conexao.close()
    return render_template("servico_form.html", processos=listar_processos())


# ---------------------------------------------------------------------
# Equipe do Serviço (Colaboradores + Servico_Equipe)
# ---------------------------------------------------------------------
def listar_servicos():
    """Lista os serviços existentes (processo + os), usada para popular
    o <select> do formulário de Equipe — 'os' é o identificador que
    diferencia serviços dentro do mesmo processo."""
    conexao = conectar()
    servicos = conexao.execute(
        "SELECT id_servico, processo, os, servicos FROM Servicos ORDER BY rowid DESC"
    ).fetchall()
    conexao.close()
    return servicos


@app.route("/equipe/novo", methods=["GET", "POST"])
def equipe_novo():
    if request.method == "POST":
        id_servico = request.form["id_servico"]
        # Um nome por linha na textarea. strip() remove espaços extras,
        # e o filter(None, ...) descarta linhas em branco.
        nomes = [
            linha.strip()
            for linha in request.form["nomes"].splitlines()
            if linha.strip()
        ]
        if len(nomes) < 3 or len(nomes) > 10:
            flash("Informe entre 3 e 10 nomes (um por linha).", "danger")
            return render_template("equipe_form.html", servicos=listar_servicos())

        conexao = conectar()
        try:
            for nome in nomes:
                # INSERT OR IGNORE: se o colaborador já existir (nome_colaborador
                # é UNIQUE), não faz nada e não gera erro.
                conexao.execute(
                    "INSERT OR IGNORE INTO Colaboradores (nome_colaborador) VALUES (?)",
                    (nome,),
                )
                id_colaborador = conexao.execute(
                    "SELECT id_colaborador FROM Colaboradores WHERE nome_colaborador = ?",
                    (nome,),
                ).fetchone()["id_colaborador"]
                # INSERT OR IGNORE aqui evita erro se a pessoa já estiver
                # escalada nesse mesmo serviço (chave composta impede duplicata).
                conexao.execute(
                    "INSERT OR IGNORE INTO Servico_Equipe (id_servico, id_colaborador) VALUES (?, ?)",
                    (id_servico, id_colaborador),
                )
            conexao.commit()
            flash(f"Equipe de {len(nomes)} pessoa(s) registrada com sucesso!", "success")
            return redirect(url_for("index"))
        except sqlite3.IntegrityError as erro:
            flash(f"Erro ao salvar equipe: {erro}", "danger")
        finally:
            conexao.close()
    return render_template("equipe_form.html", servicos=listar_servicos())


# ---------------------------------------------------------------------
# Avaliacoes_Brutas
# ---------------------------------------------------------------------
@app.route("/avaliacao/novo", methods=["GET", "POST"])
def avaliacao_novo():
    if request.method == "POST":
        dados = (
            request.form["processo"],
            request.form.get("data") or None,
            request.form.get("ano") or None,
            request.form.get("mes") or None,
            request.form.get("nota_pontualidade_coord") or None,
            request.form.get("nota_limpeza_embalagem") or None,
            request.form.get("nota_cortesia_carregamento") or None,
            request.form.get("nota_tecnica_cortesia") or None,
            request.form.get("comentario") or None,
        )
        conexao = conectar()
        try:
            conexao.execute(
                """
                INSERT INTO Avaliacoes_Brutas (
                    processo, data, ano, mes, nota_pontualidade_coord,
                    nota_limpeza_embalagem, nota_cortesia_carregamento,
                    nota_tecnica_cortesia, comentario
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                dados,
            )
            conexao.commit()
            flash("Avaliação registrada com sucesso!", "success")
            return redirect(url_for("index"))
        except sqlite3.IntegrityError as erro:
            flash(f"Erro ao salvar avaliação: {erro}", "danger")
        finally:
            conexao.close()
    return render_template("avaliacao_form.html", processos=listar_processos())


if __name__ == "__main__":
    # host="0.0.0.0" é necessário para o app ficar acessível de fora do
    # container quando rodado via Docker. Rodando localmente (fora do
    # Docker), "0.0.0.0" também funciona normalmente, então não precisa
    # mudar nada entre os dois cenários.
    app.run(host="0.0.0.0", port=5000, debug=True)
