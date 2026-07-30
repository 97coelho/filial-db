import sqlite3
import pandas as pd
import numpy as np

# Conectar ao banco de dados e garantir que as chaves estrangeiras estejam ativas
conn = sqlite3.connect('mudancas_filial.db')
conn.execute("PRAGMA foreign_keys = ON")
cursor = conn.cursor()

# Função auxiliar para tratar dados nulos
def NoneIfNa(val):
    if pd.isna(val) or val == '' or val == 'nan':
        return None
    return val

# Função auxiliar para conversão segura
def safe_float(val):
    if pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan':
        return None
    try:
        return float(val)
    except:
        return None
        
def safe_int(val):
    if pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan':
        return None
    try:
        return int(float(val))
    except:
        return None

def safe_str(val):
    if pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan':
        return None
    return str(val).strip()

print("Lendo dados da planilha preenchida...")

# Ler a planilha ODS, ignorando as 3 primeiras linhas de instruções/cabeçalhos falsos (pulando rows 0, 1, 2 = skiprows=3 na verdade vamos manter a linha 0 original porque é o cabeçalho oficial que usamos para guiar no pandas)
# Mas lendo pelo pandas com engine odf:
try:
    # Ler Agenda
    df_agenda = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Agenda', engine='odf', skiprows=3, header=None)
    # Ler colunas verdadeiras da linha 0
    df_cols = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Agenda', engine='odf', nrows=0)
    df_agenda.columns = df_cols.columns
    
    # Ler Clientes
    df_clientes = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Clientes', engine='odf', skiprows=3, header=None)
    df_cols = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Clientes', engine='odf', nrows=0)
    df_clientes.columns = df_cols.columns
    
    # Ler Servicos
    df_servicos = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Servicos', engine='odf', skiprows=3, header=None)
    df_cols = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Servicos', engine='odf', nrows=0)
    df_servicos.columns = df_cols.columns
    
    # Ler Servicos_Equipe
    df_equipe = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Servicos_Equipe', engine='odf', skiprows=3, header=None)
    df_cols = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Servicos_Equipe', engine='odf', nrows=0)
    df_equipe.columns = df_cols.columns
    
    # Ler Avaliacoes
    df_avaliacoes = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Avaliacoes_Brutas', engine='odf', skiprows=3, header=None)
    df_cols = pd.read_excel('template_migracao_dados_preenchido.ods', sheet_name='Avaliacoes_Brutas', engine='odf', nrows=0)
    df_avaliacoes.columns = df_cols.columns

except Exception as e:
    print(f"Erro ao ler a planilha: {e}")
    exit(1)


# Iniciar transação
try:
    print("Iniciando inserção no banco...")
    
    # IMPORTANTE: Desligamos temporariamente as FKs porque os dados podem ter alguma inconsistência (processo em Serviço que sumiu da Agenda, etc). Mas o ideal é manter ON e tratar.
    # Vamos manter ON e capturar erros
    
    # 1. Inserir AGENDA
    print(f"-> Inserindo {len(df_agenda)} registros na Agenda...")
    for _, row in df_agenda.iterrows():
        processo = safe_str(row.get('processo'))
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

    # 2. Inserir CLIENTES
    print(f"-> Inserindo {len(df_clientes)} registros em Clientes...")
    for _, row in df_clientes.iterrows():
        processo = safe_str(row.get('processo'))
        if not processo: continue
        
        # Ignorar se o processo não estiver na agenda para não quebrar a FK
        cursor.execute("SELECT 1 FROM Agenda WHERE processo = ?", (processo,))
        if not cursor.fetchone():
            print(f"   Aviso: Processo {processo} ignorado em Clientes (não existe na Agenda).")
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

    # 3. Inserir SERVIÇOS
    print(f"-> Inserindo {len(df_servicos)} registros em Servicos...")
    # Precisamos guardar o mapeamento de (processo, os) -> id_servico recém gerado para poder popular a tabela Servico_Equipe depois
    mapa_servicos = {}
    
    for _, row in df_servicos.iterrows():
        processo = safe_str(row.get('processo'))
        if not processo: continue
        
        cursor.execute("SELECT 1 FROM Agenda WHERE processo = ?", (processo,))
        if not cursor.fetchone():
            print(f"   Aviso: Processo {processo} ignorado em Servicos (não existe na Agenda).")
            continue
            
        os = safe_str(row.get('os'))
        
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
        # Como pode haver múltiplas pernas com a mesma OS, vamos salvar em uma lista no dicionário
        chave = (processo, os)
        if chave not in mapa_servicos:
            mapa_servicos[chave] = []
        mapa_servicos[chave].append(id_servico)

    # 4. Inserir EQUIPE
    print(f"-> Inserindo {len(df_equipe)} registros em Colaboradores/Equipe...")
    # Primeiro obter ou criar os colaboradores
    for _, row in df_equipe.iterrows():
        processo = safe_str(row.get('processo'))
        os = safe_str(row.get('os'))
        nome = safe_str(row.get('nome_colaborador'))
        
        if not processo or not nome: continue
        
        # 1. Garantir que o colaborador exista na tabela Colaboradores
        cursor.execute("SELECT id_colaborador FROM Colaboradores WHERE nome_colaborador = ?", (nome,))
        result = cursor.fetchone()
        
        if result:
            id_colab = result[0]
        else:
            cursor.execute("INSERT INTO Colaboradores (nome_colaborador) VALUES (?)", (nome,))
            id_colab = cursor.lastrowid
            
        # 2. Ligar em Servico_Equipe
        # Uma equipe listada numa linha da planilha tem processo e os.
        # Mas nós vimos que podem existir MÚLTIPLOS id_servico para o par (processo, os) se for serviço particionado.
        # A regra geral é associar a equipe a todos os serviços com aquela OS/Processo.
        chave = (processo, os)
        ids_servico = mapa_servicos.get(chave, [])
        
        for id_servico in ids_servico:
            try:
                cursor.execute("""
                    INSERT INTO Servico_Equipe (id_servico, id_colaborador) 
                    VALUES (?, ?)
                """, (id_servico, id_colab))
            except sqlite3.IntegrityError:
                # Ignorar caso já exista o par (já inserido)
                pass

    # 5. Inserir AVALIACOES BRUTAS
    print(f"-> Inserindo {len(df_avaliacoes)} registros em Avaliacoes_Brutas...")
    for _, row in df_avaliacoes.iterrows():
        processo = safe_str(row.get('processo'))
        if not processo: continue
        
        cursor.execute("SELECT 1 FROM Agenda WHERE processo = ?", (processo,))
        if not cursor.fetchone():
            print(f"   Aviso: Processo {processo} ignorado em Avaliacoes (não existe na Agenda).")
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

    conn.commit()
    print("\nSUCESSO: Banco de dados populado com os dados da planilha de migração!")

except Exception as e:
    conn.rollback()
    print(f"\nERRO DURANTE A INSERÇÃO. Rollback executado. Detalhes: {e}")

finally:
    conn.close()
