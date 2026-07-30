import pandas as pd
from odf.opendocument import load
from odf.table import Table, TableRow, TableCell
from odf.text import P

# 1. Recarregar os dados brutos e tratar os nomes das colunas com cuidado
df_avaliacoes = pd.read_csv('data_old/avaliacao_bruta.CSV', sep=';', encoding='ISO-8859-1')

# Vamos pegar a última coluna independente do nome (já que o nome tem espaços e quebras de linha estranhas)
col_comentario = df_avaliacoes.columns[-1]

avaliacoes_out = []
for _, row in df_avaliacoes.iterrows():
    processo = str(row['Processo Nº']).strip() if pd.notna(row.get('Processo Nº')) else None
    if not processo or processo == 'nan':
        continue
        
    comentario = str(row[col_comentario]).strip() if pd.notna(row[col_comentario]) else ''
    if comentario == 'nan':
        comentario = ''
        
    # Tratamento de data (reutilizado)
    val_data = row.get('Data')
    data = None
    obs_d = None
    if pd.notna(val_data) and str(val_data).strip() != '':
        val_str = str(val_data).strip()
        import re
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', val_str):
            try:
                data = pd.to_datetime(val_str, format='%d/%m/%Y').strftime('%Y-%m-%d')
            except:
                obs_d = val_str
        elif re.match(r'^\d{4}-\d{2}-\d{2}$', val_str):
            try:
                data = pd.to_datetime(val_str, format='%Y-%m-%d').strftime('%Y-%m-%d')
            except:
                obs_d = val_str
        else:
            obs_d = val_str
            
    if obs_d:
        comentario += f" [Data Original: {obs_d}]"
        
    def to_float(v):
        if pd.isna(v) or str(v).strip() == '': return None
        try: return float(str(v).replace(',', '.'))
        except: return None
        
    def to_int(v):
        if pd.isna(v) or str(v).strip() == '': return None
        try: return int(float(str(v).replace(',', '.')))
        except: return None

    avaliacoes_out.append({
        'processo': processo,
        'data': data,
        'ano': to_int(row.get('Ano')),
        'mes': to_int(row.get('Mês')),
        'nota_pontualidade_coord': to_float(row.get('Pontualidade/\nCoordenação')),
        'nota_limpeza_embalagem': to_float(row.get('Limpeza/\nQualidade de Embalagem')),
        'nota_cortesia_carregamento': to_float(row.get('Cortesia/\nQualidade de Carregamento')),
        'nota_tecnica_cortesia': to_float(row.get('Técnica/\nCortesia')),
        'comentario': comentario.strip() if comentario.strip() else None
    })

df_avaliacoes_out = pd.DataFrame(avaliacoes_out)
print(f"Comentários extraídos (não nulos): {df_avaliacoes_out['comentario'].notna().sum()} de {len(df_avaliacoes_out)}")

# 2. Atualizar apenas a aba de Avaliacoes no arquivo já gerado
doc = load('template_migracao_dados_preenchido.ods')
sheet_name = 'Avaliacoes_Brutas'

for table in doc.spreadsheet.getElementsByType(Table):
    if table.getAttribute('name') == sheet_name:
        rows = table.getElementsByType(TableRow)
        
        # Manter as 3 primeiras (cabeçalho, dica, exemplo)
        header_rows = []
        for i in range(min(len(rows), 3)):
            header_rows.append(rows[i])
            
        while table.hasChildNodes():
            table.removeChild(table.firstChild)
            
        for r in header_rows:
            table.addElement(r)
            
        import numpy as np
        for _, row_data in df_avaliacoes_out.iterrows():
            tr = TableRow()
            for col in df_avaliacoes_out.columns:
                val = row_data[col]
                tc = TableCell()
                
                if pd.notna(val) and val is not None:
                    if isinstance(val, float):
                        tc.setAttribute('valuetype', 'float')
                        tc.setAttribute('value', str(val))
                        p = P(text=str(val))
                    elif isinstance(val, int) or isinstance(val, np.integer):
                        tc.setAttribute('valuetype', 'float')
                        tc.setAttribute('value', str(val))
                        p = P(text=str(val))
                    else:
                        tc.setAttribute('valuetype', 'string')
                        p = P(text=str(val))
                    tc.addElement(p)
                tr.addElement(tc)
            table.addElement(tr)
        break

doc.save('template_migracao_dados_preenchido.ods')
print("Aba de Avaliacoes_Brutas atualizada com sucesso.")
