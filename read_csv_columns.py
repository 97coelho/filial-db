import pandas as pd

try:
    df_agenda = pd.read_csv('data_old/agenda.CSV', sep=';', encoding='ISO-8859-1')
    print(f"Agenda cols: {list(df_agenda.columns)}")
except Exception as e:
    print(f"Erro Agenda: {e}")

try:
    df_servicos = pd.read_csv('data_old/servicos.CSV', sep=';', encoding='ISO-8859-1')
    print(f"Servicos cols: {list(df_servicos.columns)}")
except Exception as e:
    print(f"Erro Servicos: {e}")

try:
    df_avaliacoes = pd.read_csv('data_old/avaliacao_bruta.CSV', sep=';', encoding='ISO-8859-1')
    print(f"Avaliacoes cols: {list(df_avaliacoes.columns)}")
except Exception as e:
    print(f"Erro Avaliacoes: {e}")
