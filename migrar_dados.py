import pandas as pd
import numpy as np
import re

def clean_col_name(col):
    return str(col).strip().replace('\n', ' ')

def to_date_or_null(val, original_val=None):
    if pd.isna(val) or str(val).strip() == '':
        return None, original_val
    val_str = str(val).strip()
    # Verifica se parece data
    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', val_str):
        try:
            d = pd.to_datetime(val_str, format='%d/%m/%Y').strftime('%Y-%m-%d')
            return d, None
        except:
            return None, val_str
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', val_str):
        try:
            d = pd.to_datetime(val_str, format='%Y-%m-%d').strftime('%Y-%m-%d')
            return d, None
        except:
            return None, val_str
    return None, val_str

def to_float(val):
    if pd.isna(val) or str(val).strip() == '':
        return None
    try:
        return float(str(val).replace(',', '.'))
    except:
        return None

def to_int(val):
    if pd.isna(val) or str(val).strip() == '':
        return None
    try:
        return int(float(str(val).replace(',', '.')))
    except:
        return None

# Load CSVs
df_agenda = pd.read_csv('data_old/agenda.CSV', sep=';', encoding='ISO-8859-1')
df_agenda.columns = [clean_col_name(c) for c in df_agenda.columns]

df_servicos = pd.read_csv('data_old/servicos.CSV', sep=';', encoding='ISO-8859-1')
df_servicos.columns = [clean_col_name(c) for c in df_servicos.columns]

df_avaliacoes = pd.read_csv('data_old/avaliacao_bruta.CSV', sep=';', encoding='ISO-8859-1')
df_avaliacoes.columns = [clean_col_name(c) for c in df_avaliacoes.columns]

# Encontrar processos órfãos em serviços e avaliações
processos_agenda = set(df_agenda['Processo'].dropna().astype(str).str.strip())
processos_servicos = set(df_servicos['Processo'].dropna().astype(str).str.strip())
processos_avaliacoes = set(df_avaliacoes['Processo Nº'].dropna().astype(str).str.strip())

processos_orfaos = (processos_servicos.union(processos_avaliacoes)) - processos_agenda

novas_linhas_agenda = []
for p in processos_orfaos:
    if p and str(p) != 'nan':
        novas_linhas_agenda.append({
            'Processo': p,
            'Observações': 'Processo órfão importado para garantir integridade'
        })

if novas_linhas_agenda:
    df_agenda = pd.concat([df_agenda, pd.DataFrame(novas_linhas_agenda)], ignore_index=True)


# ==========================================
# 1. AGENDA
# ==========================================
agenda_out = []
for _, row in df_agenda.iterrows():
    processo = str(row['Processo']).strip() if pd.notna(row.get('Processo')) else None
    if not processo or processo == 'nan':
        continue
        
    obs = str(row.get('Observações', '')) if pd.notna(row.get('Observações')) else ''
    
    rec_em, obs_rec = to_date_or_null(row.get('Recebido em'))
    d_a_ini, obs_dai = to_date_or_null(row.get('Data A inicial'))
    d_b_ini, obs_dbi = to_date_or_null(row.get('Data B inicial'))
    d_a_ofe, obs_dao = to_date_or_null(row.get('Data A ofertada'))
    d_b_ofe, obs_dbo = to_date_or_null(row.get('Data B ofertada'))
    
    anotacoes = obs
    for obs_item in [obs_rec, obs_dai, obs_dbi, obs_dao, obs_dbo]:
        if obs_item:
            anotacoes += f" [Data inconsistente: {obs_item}]"
            
    agenda_out.append({
        'processo': processo,
        'recebido_em': rec_em,
        'data_a_inicial': d_a_ini,
        'data_b_inicial': d_b_ini,
        'data_a_ofertada': d_a_ofe,
        'data_b_ofertada': d_b_ofe,
        'volume': to_float(row.get('Volume')),
        'engradados': to_int(row.get('Engradados')),
        'caixas': to_int(row.get('Caixas')),
        'lifts': to_int(row.get('Lifts')),
        'tipo': row.get('Tipo') if pd.notna(row.get('Tipo')) else None,
        'status_agenda': row.get('Status') if pd.notna(row.get('Status')) else None,
        'origem': row.get('Origem') if pd.notna(row.get('Origem')) else None,
        'destino': row.get('Destino') if pd.notna(row.get('Destino')) else None,
        'anotacoes_agenda': anotacoes.strip() if anotacoes.strip() else None
    })

df_agenda_out = pd.DataFrame(agenda_out)

# ==========================================
# 2. CLIENTES
# ==========================================
clientes_out = []

# Tenta extrair de agenda
for _, row in df_agenda.iterrows():
    processo = str(row['Processo']).strip() if pd.notna(row.get('Processo')) else None
    if not processo or processo == 'nan':
        continue
    nome = row.get('Nome do cliente')
    if pd.notna(nome) and str(nome).strip() != '':
        clientes_out.append({
            'processo': processo,
            'nome_cliente': str(nome).strip(),
            'email': None,
            'email_agendor': None,
            'agente': None,
            'empresa': None
        })

# Tenta extrair de serviços para processos que ainda não têm cliente, ou atualiza informações
processos_com_cliente = {c['processo'] for c in clientes_out}

for _, row in df_servicos.iterrows():
    processo = str(row['Processo']).strip() if pd.notna(row.get('Processo')) else None
    if not processo or processo == 'nan':
        continue
        
    nome = row.get('Cliente')
    if pd.notna(nome) and str(nome).strip() != '' and processo not in processos_com_cliente:
        clientes_out.append({
            'processo': processo,
            'nome_cliente': str(nome).strip(),
            'email': None,
            'email_agendor': None,
            'agente': None,
            'empresa': None
        })
        processos_com_cliente.add(processo)

df_clientes_out = pd.DataFrame(clientes_out)

# ==========================================
# 3. SERVICOS
# ==========================================
servicos_out = []
servicos_equipe_out = []

for _, row in df_servicos.iterrows():
    processo = str(row['Processo']).strip() if pd.notna(row.get('Processo')) else None
    if not processo or processo == 'nan':
        continue
        
    d_ini, obs_di = to_date_or_null(row.get('data_inicio'))
    d_fim, obs_df = to_date_or_null(row.get('data_final'))
    
    anotacoes = str(row.get('Anotacoes', '')) if pd.notna(row.get('Anotacoes')) else ''
    if obs_di: anotacoes += f" [Data Inicio Inconsistente: {obs_di}]"
    if obs_df: anotacoes += f" [Data Final Inconsistente: {obs_df}]"
    
    os = str(row.get('OS')).strip() if pd.notna(row.get('OS')) else None
    
    servicos_out.append({
        'processo': processo,
        'servicos': row.get('Serviços') if pd.notna(row.get('Serviços')) else None,
        'modal': row.get('Modal') if pd.notna(row.get('Modal')) else None,
        'os': os,
        'ref_externa': row.get('Ref_Externa') if pd.notna(row.get('Ref_Externa')) else None,
        'cidade': row.get('Cidade') if pd.notna(row.get('Cidade')) else None,
        'data_inicio': d_ini,
        'data_final': d_fim,
        'm3_real': to_float(row.get('m³ real')),
        'quant_itens': to_int(row.get('quant_itens')),
        'peso_kg': to_float(row.get('Peso (kg)')),
        'peso_bruto': None,
        'peso_bruto_real_1': None,
        'peso_liquido': None,
        'peso_liquido_real_1': None,
        'etd': None,
        'eta': None,
        'liftvan': None,
        'peso_liftvan': None,
        'tara_liftvan': None,
        'icamento': None,
        'container_20': None,
        'container_40': None,
        'quant_container_20': None,
        'quant_cont_40': None,
        'contents': None,
        'empresa': row.get('Empresa') if pd.notna(row.get('Empresa')) else None,
        'tipo_cliente': row.get('Private/Booking') if pd.notna(row.get('Private/Booking')) else None,
        'status_servico': row.get('Status') if pd.notna(row.get('Status')) else None,
        'faturamento': row.get('Faturamento') if pd.notna(row.get('Faturamento')) else None,
        'fatura': row.get('Fatura') if pd.notna(row.get('Fatura')) else None,
        'coordenadora': row.get('Coordenadora') if pd.notna(row.get('Coordenadora')) else None,
        'anotacoes_servico': anotacoes.strip() if anotacoes.strip() else None
    })
    
    # Processar Equipe
    equipe_raw = str(row.get('Equipe')) if pd.notna(row.get('Equipe')) else ''
    if equipe_raw and equipe_raw.lower() != 'nan':
        # Separar por vírgula, "e" ou ponto
        equipe_raw = equipe_raw.replace('.', ',').replace(' e ', ',')
        membros = [m.strip() for m in equipe_raw.split(',') if m.strip()]
        for m in membros:
            if m:
                servicos_equipe_out.append({
                    'processo': processo,
                    'os': os,
                    'nome_colaborador': m
                })

df_servicos_out = pd.DataFrame(servicos_out)
df_servicos_equipe_out = pd.DataFrame(servicos_equipe_out)

# ==========================================
# 4. AVALIACOES BRUTAS
# ==========================================
avaliacoes_out = []
for _, row in df_avaliacoes.iterrows():
    processo = str(row['Processo Nº']).strip() if pd.notna(row.get('Processo Nº')) else None
    if not processo or processo == 'nan':
        continue
        
    data, obs_d = to_date_or_null(row.get('Data'))
    
    comentario = str(row.get('  Comentário   ', '')).strip()
    if pd.isna(row.get('  Comentário   ')):
        comentario = str(row.get('  Comentário ', '')).strip()
    if comentario == 'nan':
        comentario = ''
        
    if obs_d:
        comentario += f" [Data Original: {obs_d}]"
        
    avaliacoes_out.append({
        'processo': processo,
        'data': data,
        'ano': to_int(row.get('Ano')),
        'mes': to_int(row.get('Mês')),
        'nota_pontualidade_coord': to_float(row.get('Pontualidade/ Coordenação')),
        'nota_limpeza_embalagem': to_float(row.get('Limpeza/ Qualidade de Embalagem')),
        'nota_cortesia_carregamento': to_float(row.get('Cortesia/ Qualidade de Carregamento')),
        'nota_tecnica_cortesia': to_float(row.get('Técnica/ Cortesia')),
        'comentario': comentario.strip() if comentario.strip() else None
    })

df_avaliacoes_out = pd.DataFrame(avaliacoes_out)

# ==========================================
# GRAVAR NO ODS
# ==========================================
# Vamos ler o arquivo original e atualizar as abas
from odf.opendocument import load
from odf.table import Table, TableRow, TableCell
from odf.text import P

print(f"Escrevendo dados no arquivo ods...")

def append_df_to_ods_sheet(ods_doc, sheet_name, df, start_row_idx=3):
    """
    Adiciona os dados do DataFrame na aba sheet_name do doc odf,
    a partir do start_row_idx (0-based index). As primeiras start_row_idx linhas
    são mantidas (cabeçalho, dica, exemplo).
    """
    for table in ods_doc.spreadsheet.getElementsByType(Table):
        if table.getAttribute('name') == sheet_name:
            # Pegar as linhas existentes
            rows = table.getElementsByType(TableRow)
            
            # Garantir que temos as 3 primeiras linhas (0, 1, 2)
            header_rows = []
            for i in range(min(len(rows), start_row_idx)):
                header_rows.append(rows[i])
                
            # Limpar a tabela
            while table.hasChildNodes():
                table.removeChild(table.firstChild)
                
            # Recolocar cabeçalhos
            for r in header_rows:
                table.addElement(r)
                
            # Adicionar as novas linhas a partir do DataFrame
            # As colunas do DataFrame devem bater com o cabeçalho original
            
            for _, row_data in df.iterrows():
                tr = TableRow()
                for col in df.columns:
                    val = row_data[col]
                    tc = TableCell()
                    
                    if pd.notna(val) and val is not None:
                        # Converter o valor para string corretamente dependendo do tipo
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


try:
    doc = load('template_migracao_dados.ods')
    
    append_df_to_ods_sheet(doc, 'Agenda', df_agenda_out)
    append_df_to_ods_sheet(doc, 'Clientes', df_clientes_out)
    append_df_to_ods_sheet(doc, 'Servicos', df_servicos_out)
    append_df_to_ods_sheet(doc, 'Servicos_Equipe', df_servicos_equipe_out)
    append_df_to_ods_sheet(doc, 'Avaliacoes_Brutas', df_avaliacoes_out)
    
    doc.save('template_migracao_dados_preenchido.ods')
    print("Processo concluído com sucesso. Arquivo salvo como 'template_migracao_dados_preenchido.ods'")
    
except Exception as e:
    print(f"Erro ao salvar ODS: {e}")

