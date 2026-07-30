import pandas as pd

df_avaliacoes = pd.read_csv('data_old/avaliacao_bruta.CSV', sep=';', encoding='ISO-8859-1')
print("Colunas reais no CSV:")
for c in df_avaliacoes.columns:
    print(f"'{c}'")

print("\nAlguns valores da coluna de comentários (última):")
print(df_avaliacoes.iloc[:5, -1])
