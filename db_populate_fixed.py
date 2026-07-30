import sqlite3
import pandas as pd
import numpy as np

# Conectar ao banco de dados
conn = sqlite3.connect('mudancas_filial.db')
conn.execute("PRAGMA foreign_keys = ON")
cursor = conn.cursor()

def clean_process_id(val):
    if pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan':
        return None
    val_str = str(val).strip()
    # Se terminar com .0 (ex: 15007.0), remove
    if val_str.endswith('.0'):
        val_str = val_str[:-2]
    return val_str

def safe_float(val):
    if pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan':
        return None
    try: return float(val)
    except: return None
        
def safe_int(val):
    if pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan':
        return None
    try: return int(float(val))
    except: return None

def safe_str(val):
    if pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan':
        return None
    return str(val).strip()

print("Lendo dados da planilha preenchida...")

try:
    df_agenda = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Agenda', engine='odf', skiprows=3, header=None)
    df_cols = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Agenda', engine='odf', nrows=0)
    df_agenda.columns = df_cols.columns
    
    df_clientes = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Clientes', engine='odf', skiprows=3, header=None)
    df_cols = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Clientes', engine='odf', nrows=0)
    df_clientes.columns = df_cols.columns
    
    df_servicos = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Servicos', engine='odf', skiprows=3, header=None)
    df_cols = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Servicos', engine='odf', nrows=0)
    df_servicos.columns = df_cols.columns
    
    df_equipe = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Servicos_Equipe', engine='odf', skiprows=3, header=None)
    df_cols = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Servicos_Equipe', engine='odf', nrows=0)
    df_equipe.columns = df_cols.columns
    
    df_avaliacoes = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Avaliacoes_Brutas', engine='odf', skiprows=3, header=None)
    df_cols = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Avaliacoes_Brutas', engine='odf', nrows=0)
    df_avaliacoes.columns = df_cols.columns

except Exception as e:
    print(f"Erro ao ler a planilha: {e}")
    exit(1)


# Como rodamos o setup_db antes, vamos limpar as tabelas relacionadas à nossa carga para evitar duplicação ou mistura.
# Mas preservaremos os testes inseridos pelo setup_db.py ('PROC-...') ou melhor, se for pra limpar, limpamos tudo que seja numérico e tenha vindo da migração.
# Para manter idempotente: O INSERT OR REPLACE na Agenda resolve as sobreposições de processo. Nas outras tabelas, como não temos PK explícita (é autoincrement), poderíamos duplicar.
# Então, vamos deletar das outras tabelas onde o processo pertença à planilha.

processos_na_planilha = [clean_process_id(p) for p in df_agenda['processo'].dropna()]
# Filtra apenas os válidos
processos_na_planilha = [p for p in processos_na_planilha if p]

# Para apagar em lote:
if processos_na_planilha:
    placeholders = ','.join(['?'] * len(processos_na_planilha))
    
    # Precisamos deletar Servico_Equipe primeiro para não quebrar FK do Servicos
    # Buscar os id_servico associados a esses processos
    cursor.execute(f"SELECT id_servico FROM Servicos WHERE processo IN ({placeholders})", processos_na_planilha)
    ids_servico = [row[0] for row in cursor.fetchall()]
    
    if ids_servico:
        placeholders_servico = ','.join(['?'] * len(ids_servico))
        cursor.execute(f"DELETE FROM Servico_Equipe WHERE id_servico IN ({placeholders_servico})", ids_servico)
    
    cursor.execute(f"DELETE FROM Servicos WHERE processo IN ({placeholders})", processos_na_planilha)
    cursor.execute(f"DELETE FROM Avaliacoes_Brutas WHERE processo IN ({placeholders})", processos_na_planilha)
    cursor.execute(f"DELETE FROM Clientes WHERE processo IN ({placeholders})", processos_na_planilha)


try:
    print("Iniciando inserção corrigida no banco...")
    
    # 1. Inserir AGENDA
    print(f"-> Inserindo Agenda...")
    count_agenda = 0
    for _, row in df_agenda.iterrows():
        processo = clean_process_id(row.get('processo'))
        if not processo: continue
        
        cursor.execute("""
            INSERT OR REPLACE INTO Agenda (
                processo, recebido_em, data_a_inicial, data_b_inicial, 
                data_a_ofertada, data_b_ofertada, volume, engradados, caixas, 
                lifts, tipo, status_agenda, origem, destino, anotacoes_agenda
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            processo,
            safe_str(row.get('recebido_em')),
            safe_str(row.get('data_a_inicial')),
            safe_str(row.get('data_b_inicial')),
            safe_str(row.get('data_a_ofertada')),
            safe_str(row.get('data_b_ofertada')),
            safe_float(row.get('volume')),
            safe_int(row.get('engradados')),
            safe_int(row.get('caixas')),
            safe_int(row.get('lifts')),
            safe_str(row.get('tipo')),
            safe_str(row.get('status_agenda')),
            safe_str(row.get('origem')),
            safe_str(row.get('destino')),
            safe_str(row.get('anotacoes_agenda'))
        ))
        count_agenda += 1
    print(f"   Foram inseridos/atualizados {count_agenda} registros na Agenda.")

    # 2. Inserir CLIENTES
    print(f"-> Inserindo Clientes...")
    count_clientes = 0
    for _, row in df_clientes.iterrows():
        processo = clean_process_id(row.get('processo'))
        if not processo: continue
        
        cursor.execute("SELECT 1 FROM Agenda WHERE processo = ?", (processo,))
        if not cursor.fetchone():
            print(f"   [AVISO] Processo '{processo}' ignorado em Clientes (não existe na Agenda).")
            continue
            
        cursor.execute("""
            INSERT INTO Clientes (
                processo, nome_cliente, email, email_agendor, agente, empresa
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            processo,
            safe_str(row.get('nome_cliente', 'Sem Nome')),
            safe_str(row.get('email')),
            safe_str(row.get('email_agendor')),
            safe_str(row.get('agente')),
            safe_str(row.get('empresa'))
        ))
        count_clientes += 1
    print(f"   Foram inseridos {count_clientes} registros em Clientes.")

    # 3. Inserir SERVIÇOS
    print(f"-> Inserindo Servicos...")
    mapa_servicos = {}
    count_servicos = 0
    for _, row in df_servicos.iterrows():
        processo = clean_process_id(row.get('processo'))
        if not processo: continue
        
        cursor.execute("SELECT 1 FROM Agenda WHERE processo = ?", (processo,))
        if not cursor.fetchone():
            print(f"   [AVISO] Processo '{processo}' ignorado em Servicos (não existe na Agenda).")
            continue
            
        os = clean_process_id(row.get('os'))
        
        cursor.execute("""
            INSERT INTO Servicos (
                processo, servicos, modal, os, ref_externa, cidade,
                data_inicio, data_final, m3_real, quant_itens, peso_kg,
                peso_bruto, peso_bruto_real_1, peso_liquido, peso_liquido_real_1,
                etd, eta, liftvan, peso_liftvan, tara_liftvan, icamento,
                container_20, container_40, quant_container_20, quant_cont_40,
                contents, empresa, tipo_cliente, status_servico, faturamento,
                fatura, coordenadora, anotacoes_servico
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            processo,
            safe_str(row.get('servicos')),
            safe_str(row.get('modal')),
            os,
            safe_str(row.get('ref_externa')),
            safe_str(row.get('cidade')),
            safe_str(row.get('data_inicio')),
            safe_str(row.get('data_final')),
            safe_float(row.get('m3_real')),
            safe_int(row.get('quant_itens')),
            safe_float(row.get('peso_kg')),
            safe_float(row.get('peso_bruto')),
            safe_float(row.get('peso_bruto_real_1')),
            safe_float(row.get('peso_liquido')),
            safe_float(row.get('peso_liquido_real_1')),
            safe_str(row.get('etd')),
            safe_str(row.get('eta')),
            safe_str(row.get('liftvan')),
            safe_float(row.get('peso_liftvan')),
            safe_float(row.get('tara_liftvan')),
            safe_str(row.get('icamento')),
            safe_str(row.get('container_20')),
            safe_str(row.get('container_40')),
            safe_int(row.get('quant_container_20')),
            safe_int(row.get('quant_cont_40')),
            safe_str(row.get('contents')),
            safe_str(row.get('empresa')),
            safe_str(row.get('tipo_cliente')),
            safe_str(row.get('status_servico')),
            safe_str(row.get('faturamento')),
            safe_str(row.get('fatura')),
            safe_str(row.get('coordenadora')),
            safe_str(row.get('anotacoes_servico'))
        ))
        
        id_servico = cursor.lastrowid
        count_servicos += 1
        
        chave = (processo, os)
        if chave not in mapa_servicos:
            mapa_servicos[chave] = []
        mapa_servicos[chave].append(id_servico)
    print(f"   Foram inseridos {count_servicos} registros em Servicos.")

    # 4. Inserir EQUIPE
    print(f"-> Inserindo Colaboradores/Equipe...")
    count_equipe = 0
    for _, row in df_equipe.iterrows():
        processo = clean_process_id(row.get('processo'))
        os = clean_process_id(row.get('os'))
        nome = safe_str(row.get('nome_colaborador'))
        
        if not processo or not nome: continue
        
        cursor.execute("SELECT id_colaborador FROM Colaboradores WHERE nome_colaborador = ?", (nome,))
        result = cursor.fetchone()
        
        if result:
            id_colab = result[0]
        else:
            cursor.execute("INSERT INTO Colaboradores (nome_colaborador) VALUES (?)", (nome,))
            id_colab = cursor.lastrowid
            
        chave = (processo, os)
        ids_servico = mapa_servicos.get(chave, [])
        
        for id_servico in ids_servico:
            try:
                cursor.execute("""
                    INSERT INTO Servico_Equipe (id_servico, id_colaborador) 
                    VALUES (?, ?)
                """, (id_servico, id_colab))
                count_equipe += 1
            except sqlite3.IntegrityError:
                pass
    print(f"   Foram feitas {count_equipe} ligações Servico_Equipe.")

    # 5. Inserir AVALIACOES BRUTAS
    print(f"-> Inserindo Avaliacoes_Brutas...")
    count_avaliacoes = 0
    for _, row in df_avaliacoes.iterrows():
        processo = clean_process_id(row.get('processo'))
        if not processo: continue
        
        cursor.execute("SELECT 1 FROM Agenda WHERE processo = ?", (processo,))
        if not cursor.fetchone():
            print(f"   [AVISO] Processo '{processo}' ignorado em Avaliacoes (não existe na Agenda).")
            continue
            
        cursor.execute("""
            INSERT INTO Avaliacoes_Brutas (
                processo, data, ano, mes, nota_pontualidade_coord,
                nota_limpeza_embalagem, nota_cortesia_carregamento,
                nota_tecnica_cortesia, comentario
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            processo,
            safe_str(row.get('data')),
            safe_int(row.get('ano')),
            safe_int(row.get('mes')),
            safe_float(row.get('nota_pontualidade_coord')),
            safe_float(row.get('nota_limpeza_embalagem')),
            safe_float(row.get('nota_cortesia_carregamento')),
            safe_float(row.get('nota_tecnica_cortesia')),
            safe_str(row.get('comentario'))
        ))
        count_avaliacoes += 1
    print(f"   Foram inseridas {count_avaliacoes} avaliações.")

    conn.commit()
    print("\nSUCESSO TOTAL! Banco de dados populado.")

except Exception as e:
    conn.rollback()
    print(f"\nERRO DURANTE A INSERÇÃO. Rollback executado. Detalhes: {e}")

finally:
    conn.close()

# TESTAR
conn = sqlite3.connect('mudancas_filial.db')
print("\n--- NOVO ESTADO DO BANCO (CONTAGENS) ---")
tables = ['Agenda', 'Clientes', 'Servicos', 'Colaboradores', 'Servico_Equipe', 'Avaliacoes_Brutas']
for t in tables:
    count = pd.read_sql(f"SELECT COUNT(*) as c FROM {t}", conn).iloc[0,0]
    print(f"{t}: {count} registros")
conn.close()
