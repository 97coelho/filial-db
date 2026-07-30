#!/usr/bin/env python3
"""
setup_db.py
-----------
Script didático para criar e popular o banco `mudancas_filial.db` (SQLite),
substituindo o antigo controle em Microsoft Access da filial de mudanças
internacionais.

O que este script faz, passo a passo:
  1. Conecta (ou cria, se não existir) o arquivo mudancas_filial.db
  2. Executa o DDL do arquivo schema.sql (tabelas + view)
  3. Insere um conjunto de dados de teste cobrindo todo o fluxo:
     Cliente -> Agenda -> Serviços -> Equipe (Colaboradores) -> Avaliação
  4. Faz um JOIN entre Agenda e Servicos, provando que origem/destino
     definidos na Agenda "aparecem" corretamente ao lado do detalhamento
     de cada serviço
  5. Consulta Servico_Equipe + Colaboradores, provando que dá para listar
     a equipe de cada serviço e contar quantos serviços cada pessoa fez
  6. Consulta a VIEW Comissoes_Calculadas e exibe o resultado com pandas

IMPORTANTE: se você já tinha um mudancas_filial.db criado ANTES desta
versão do schema (com as colunas antigas 'avaliacao' e 'equipe' em
Servicos), apague o arquivo antes de rodar este script — o schema mudou
de forma incompatível (colunas removidas, tabelas novas), e
CREATE TABLE IF NOT EXISTS não altera uma tabela que já existe com
estrutura diferente.

Como rodar no Ubuntu:
    python3 setup_db.py

Pré-requisitos:
    pip install pandas   # sqlite3 já vem na biblioteca padrão do Python
"""

import sqlite3          # biblioteca padrão do Python para falar com bancos SQLite
from pathlib import Path
import pandas as pd     # usado só para deixar as consultas bonitas no terminal

# ----------------------------------------------------------------------
# 1. Configuração de caminhos
# ----------------------------------------------------------------------
# Path(__file__).parent = pasta onde este script está salvo.
# Assim o banco é sempre criado ao lado do script, não importa de onde
# você rode o comando "python3 setup_db.py".
PASTA_ATUAL = Path(__file__).parent
CAMINHO_DB = PASTA_ATUAL / "mudancas_filial.db"
CAMINHO_SCHEMA = PASTA_ATUAL / "schema.sql"


def conectar_banco() -> sqlite3.Connection:
    """
    Abre uma conexão com o arquivo mudancas_filial.db.
    Se o arquivo não existir, o SQLite cria um banco novo e vazio
    automaticamente — não precisamos de um comando "CREATE DATABASE".
    """
    conexao = sqlite3.connect(CAMINHO_DB)
    # Ativa a checagem de chaves estrangeiras nesta conexão específica.
    # No SQLite essa checagem vem desligada por padrão em toda nova conexão.
    conexao.execute("PRAGMA foreign_keys = ON;")
    return conexao


def criar_estrutura(conexao: sqlite3.Connection) -> None:
    """
    Lê o arquivo schema.sql (DDL com CREATE TABLE / CREATE VIEW) e
    executa tudo de uma vez com executescript().
    Usar um .sql separado facilita revisar/editar a estrutura do banco
    sem mexer na lógica Python.
    """
    sql_ddl = CAMINHO_SCHEMA.read_text(encoding="utf-8")
    conexao.executescript(sql_ddl)
    conexao.commit()
    print("✅ Estrutura (tabelas + view) criada/verificada com sucesso.")


def limpar_dados_de_teste(conexao: sqlite3.Connection) -> None:
    """
    Apaga dados de execuções anteriores deste script para que ele possa
    ser rodado várias vezes seguidas sem erro de chave duplicada
    (processo é TEXT PRIMARY KEY em Agenda, então rodar duas vezes sem
    limpar geraria um IntegrityError).
    A ordem do DELETE respeita as chaves estrangeiras: primeiro as
    tabelas "filhas", depois a tabela "mãe" (Agenda).
    """
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM Avaliacoes_Brutas;")
    cursor.execute("DELETE FROM Servico_Equipe;")
    cursor.execute("DELETE FROM Colaboradores;")
    cursor.execute("DELETE FROM Servicos;")
    cursor.execute("DELETE FROM Clientes;")
    cursor.execute("DELETE FROM Agenda;")
    conexao.commit()


def inserir_dados_de_teste(conexao: sqlite3.Connection) -> None:
    """
    Insere um fluxo completo de dados fictícios (dummy data):
    2 processos de mudança, cada um com cliente, agenda, serviços
    e avaliações — o suficiente para exercitar todos os JOINs e a VIEW.

    Usamos "?" como placeholder nas queries (parametrização) em vez de
    concatenar strings. Isso é uma boa prática obrigatória: evita erros
    de sintaxe com aspas em texto e protege contra SQL Injection.
    """
    cursor = conexao.cursor()

    # --- Agenda: nasce o processo, com volumetria e origem/destino ---
    cursor.executemany(
        """
        INSERT INTO Agenda (
            processo, recebido_em, data_a_inicial, data_b_inicial,
            data_a_ofertada, data_b_ofertada, volume, engradados,
            caixas, lifts, tipo, status_agenda, origem, destino,
            anotacoes_agenda
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "PROC-2026-001", "2026-01-10", "2026-02-01", "2026-02-15",
                "2026-02-03", "2026-02-17", 45.5, 3, 60, 1,
                "Internacional", "Em andamento", "Brasília, BR",
                "Lisboa, PT", "Cliente pediu prioridade no ícamento",
            ),
            (
                "PROC-2026-002", "2026-01-15", "2026-03-01", "2026-03-20",
                "2026-03-05", "2026-03-22", 22.0, 1, 30, 0,
                "Internacional", "Concluído", "São Paulo, BR",
                "Milão, IT", None,
            ),
        ],
    )

    # --- Clientes: histórico cadastral, vinculado ao processo ---
    cursor.executemany(
        """
        INSERT INTO Clientes (
            processo, nome_cliente, email, email_agendor, agente, empresa
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "PROC-2026-001", "Mariana Costa", "mariana.costa@email.com",
                "mariana.agendor@email.com", "Agente Lisboa Mudanças",
                "Gerson & Grey",
            ),
            (
                "PROC-2026-002", "Fábio Reis", "fabio.reis@email.com",
                "fabio.agendor@email.com", "Agente Milão Relocation",
                "Gerson & Grey",
            ),
        ],
    )

    # --- Servicos: detalhamento operacional de cada processo ---
    cursor.executemany(
        """
        INSERT INTO Servicos (
            processo, servicos, modal, os, ref_externa, cidade,
            data_inicio, data_final, m3_real, quant_itens, peso_kg,
            peso_bruto, peso_bruto_real_1, peso_liquido,
            peso_liquido_real_1, etd, eta, liftvan, peso_liftvan,
            tara_liftvan, icamento, container_20, container_40,
            quant_container_20, quant_cont_40, contents, empresa,
            tipo_cliente, status_servico, faturamento,
            fatura, coordenadora, anotacoes_servico
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        [
            (
                "PROC-2026-001", "Embalagem + Transporte Marítimo", "Marítimo",
                "OS-4451", "REF-EXT-991", "Brasília", "2026-02-01",
                "2026-02-14", 44.8, 120, 3200.0, 3400.0, 3390.0,
                3200.0, 3195.0, "2026-02-05", "2026-03-01", "LV-002",
                1800.0, 350.0, "Guindaste", "Não", "Sim", 0, 1,
                "Móveis e utensílios domésticos", "Gerson & Grey",
                "Residencial", "Concluído", "Faturado",
                "NF-8821", "Ana Paula",
                "Cliente elogiou pontualidade da equipe",
            ),
            (
                "PROC-2026-002", "Embalagem + Transporte Aéreo", "Aéreo",
                "OS-4452", "REF-EXT-992", "São Paulo", "2026-03-01",
                "2026-03-10", 21.6, 58, 1500.0, 1600.0, 1590.0,
                1500.0, 1495.0, "2026-03-04", "2026-03-06", None,
                None, None, "Manual", "Não", "Não", 0, 0,
                "Roupas e itens pessoais", "Gerson & Grey", "Residencial",
                "Concluído", "Faturado", "NF-8830", "Carla Lima",
                None,
            ),
        ],
    )

    # --- Colaboradores: cadastro único de cada pessoa escalável em equipes ---
    # INSERT OR IGNORE evita erro caso o nome já exista (nome_colaborador é UNIQUE)
    cursor.executemany(
        "INSERT OR IGNORE INTO Colaboradores (nome_colaborador) VALUES (?)",
        [
            ("Ana Paula",), ("Bruno Nogueira",), ("Carlos Eduardo",),
            ("Carla Lima",), ("Douglas Faria",),
        ],
    )
    conexao.commit()

    # --- Servico_Equipe: liga cada serviço às pessoas que participaram dele ---
    # Aqui buscamos os IDs técnicos (id_servico, id_colaborador) a partir dos
    # códigos de negócio (os, nome_colaborador) que fazem mais sentido para
    # quem está digitando os dados.
    equipe_por_os = {
        "OS-4451": ["Ana Paula", "Bruno Nogueira", "Carlos Eduardo"],
        "OS-4452": ["Carla Lima", "Douglas Faria"],
    }
    for numero_os, nomes in equipe_por_os.items():
        id_servico = cursor.execute(
            "SELECT id_servico FROM Servicos WHERE os = ?", (numero_os,)
        ).fetchone()[0]
        for nome in nomes:
            id_colaborador = cursor.execute(
                "SELECT id_colaborador FROM Colaboradores WHERE nome_colaborador = ?",
                (nome,),
            ).fetchone()[0]
            cursor.execute(
                "INSERT OR IGNORE INTO Servico_Equipe (id_servico, id_colaborador) VALUES (?, ?)",
                (id_servico, id_colaborador),
            )

    # --- Avaliacoes_Brutas: notas por processo (podem ser várias) ---
    cursor.executemany(
        """
        INSERT INTO Avaliacoes_Brutas (
            processo, data, ano, mes, nota_pontualidade_coord,
            nota_limpeza_embalagem, nota_cortesia_carregamento,
            nota_tecnica_cortesia, comentario
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("PROC-2026-001", "2026-02-16", 2026, 2, 10.0, 9.0, 9.5, 9.0,
             "Excelente atendimento da coordenadora"),
            ("PROC-2026-001", "2026-02-20", 2026, 2, 9.0, 8.5, 9.0, 9.5,
             "Pequeno atraso, mas resolvido rapidamente"),
            ("PROC-2026-002", "2026-03-11", 2026, 3, 8.0, 8.0, 7.5, 8.5,
             "Bom serviço, embalagem poderia ser mais cuidadosa"),
        ],
    )

    conexao.commit()
    print("✅ Dados de teste inseridos (2 processos completos).")


def consultar_join_agenda_servicos(conexao: sqlite3.Connection) -> None:
    """
    Prova de integração: um JOIN entre Agenda e Servicos usando
    'processo' como elo comum. Mostra que origem/destino (que vivem
    só em Agenda) aparecem corretamente ao lado dos detalhes técnicos
    de cada serviço (que vivem em Servicos) — sem nenhuma duplicação
    de dado entre as duas tabelas.
    """
    query = """
        SELECT
            a.processo,
            a.origem,
            a.destino,
            a.volume       AS volume_m3_agendado,
            a.status_agenda,
            s.servicos,
            s.modal,
            s.m3_real,
            s.status_servico
        FROM Agenda AS a
        JOIN Servicos AS s ON a.processo = s.processo
        ORDER BY a.processo;
    """
    df = pd.read_sql_query(query, conexao)
    print("\n=== JOIN Agenda + Servicos (origem/destino integrados) ===")
    print(df.to_string(index=False))


def consultar_equipe_por_servico(conexao: sqlite3.Connection) -> None:
    """
    Prova da normalização de 'equipe': lista cada serviço com os
    colaboradores que participaram dele, agregados numa única string
    só para exibição (GROUP_CONCAT), embora no banco cada pessoa
    esteja em uma linha própria na tabela Servico_Equipe.
    """
    query = """
        SELECT
            s.processo,
            s.os,
            GROUP_CONCAT(c.nome_colaborador, ', ') AS equipe_escalada
        FROM Servicos AS s
        JOIN Servico_Equipe AS se ON se.id_servico = s.id_servico
        JOIN Colaboradores AS c ON c.id_colaborador = se.id_colaborador
        GROUP BY s.id_servico
        ORDER BY s.processo;
    """
    df = pd.read_sql_query(query, conexao)
    print("\n=== Equipe escalada por serviço (Servico_Equipe normalizada) ===")
    print(df.to_string(index=False))

    query_participacao = """
        SELECT
            c.nome_colaborador,
            COUNT(*) AS qtd_servicos
        FROM Servico_Equipe AS se
        JOIN Colaboradores AS c ON c.id_colaborador = se.id_colaborador
        GROUP BY c.nome_colaborador
        ORDER BY qtd_servicos DESC;
    """
    df_participacao = pd.read_sql_query(query_participacao, conexao)
    print("\n=== Quantidade de serviços por colaborador (ex: base p/ comissão) ===")
    print(df_participacao.to_string(index=False))


def consultar_view_comissoes(conexao: sqlite3.Connection) -> None:
    """
    Consulta simples na VIEW Comissoes_Calculadas, que já entrega a
    média das 4 notas por processo pronta para uso (por exemplo, para
    alimentar a planilha de comissões).
    """
    df = pd.read_sql_query("SELECT * FROM Comissoes_Calculadas ORDER BY processo;", conexao)
    print("\n=== VIEW Comissoes_Calculadas ===")
    print(df.to_string(index=False))


def main() -> None:
    conexao = conectar_banco()
    try:
        criar_estrutura(conexao)
        limpar_dados_de_teste(conexao)
        inserir_dados_de_teste(conexao)
        consultar_join_agenda_servicos(conexao)
        consultar_equipe_por_servico(conexao)
        consultar_view_comissoes(conexao)
    finally:
        # Sempre fechar a conexão, mesmo se algo der errado no meio.
        conexao.close()
        print(f"\n📁 Banco salvo em: {CAMINHO_DB.resolve()}")


if __name__ == "__main__":
    main()
