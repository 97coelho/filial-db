import sqlite3
import pandas as pd

conn = sqlite3.connect('mudancas_filial.db')

print("\n--- Contagem por Tabelas ---")
tables = ['Agenda', 'Clientes', 'Servicos', 'Colaboradores', 'Servico_Equipe', 'Avaliacoes_Brutas']
for t in tables:
    count = pd.read_sql(f"SELECT COUNT(*) as c FROM {t}", conn).iloc[0,0]
    print(f"{t}: {count} registros")

print("\n--- Amostra de Agenda ---")
print(pd.read_sql("SELECT * FROM Agenda LIMIT 2", conn).to_markdown())

print("\n--- Amostra de Avaliações ---")
print(pd.read_sql("SELECT * FROM Avaliacoes_Brutas WHERE comentario IS NOT NULL LIMIT 2", conn).to_markdown())

conn.close()
