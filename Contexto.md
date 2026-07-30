```markdown
# Guia do Banco de Dados – Mudanças Internacionais (SQLite)

## Visão Geral

Este banco de dados foi projetado para substituir um sistema legado em Microsoft Access, centralizando e otimizando o controle de mudanças internacionais em uma filial. O modelo relacional é implementado em SQLite, com foco em consultas rápidas, envio de e-mails e análises. O banco é alimentado por dados extraídos de planilhas CSV e mantém a rastreabilidade histórica dos clientes.

---

## Objetivo

- Consolidar informações de **clientes**, **agendamentos**, **serviços executados** e **avaliações** em um único repositório.
- Eliminar redundâncias do sistema antigo, garantindo que cada fato seja armazenado uma única vez.
- Fornecer uma base para cálculo de comissões (via VIEW) e futuras automações (e-mails, relatórios).
- Servir como fonte de dados confiável para aplicações Python (pandas, sqlite3).

---

## Estrutura do Banco de Dados

### 1. Tabela `Clientes`
Armazena os dados cadastrais dos clientes. Um mesmo cliente pode ter múltiplos processos (mudanças distintas) ao longo do tempo.

```sql
CREATE TABLE Clientes (
    id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
    processo TEXT NOT NULL,
    nome_cliente TEXT NOT NULL,
    email TEXT,
    email_agendor TEXT,
    agente TEXT,
    empresa TEXT,
    FOREIGN KEY (processo) REFERENCES Agenda(processo)
);
```

### 2. Tabela `Agenda`
Registra cada solicitação de mudança. É a tabela **mestra** que contém os dados de volume, origem, destino e quantidades. Cada processo é único e atua como chave primária.

```sql
CREATE TABLE Agenda (
    processo TEXT PRIMARY KEY,
    recebido_em DATE,
    data_a_inicial DATE,
    data_b_inicial DATE,
    data_a_ofertada DATE,
    data_b_ofertada DATE,
    volume REAL,
    engradados INTEGER,
    caixas INTEGER,
    lifts INTEGER,
    tipo TEXT,
    status_agenda TEXT,
    origem TEXT,
    destino TEXT,
    anotacoes_agenda TEXT
);
```

### 3. Tabela `Servicos`
Detalha a execução dos serviços para cada processo. Um processo pode ter múltiplos registros de serviço (por exemplo, diferentes pernas/dias de uma mesma OS).

```sql
CREATE TABLE Servicos (
    id_servico INTEGER PRIMARY KEY AUTOINCREMENT,
    processo TEXT NOT NULL,
    servicos TEXT,
    modal TEXT,
    os TEXT,
    ref_externa TEXT,
    cidade TEXT,
    data_inicio DATE,
    data_final DATE,
    m3_real REAL,
    quant_itens INTEGER,
    peso_kg REAL,
    peso_bruto REAL,
    peso_bruto_real_1 REAL,
    peso_liquido REAL,
    peso_liquido_real_1 REAL,
    etd DATE,
    eta DATE,
    liftvan TEXT,
    peso_liftvan REAL,
    tara_liftvan REAL,
    icamento TEXT,
    container_20 TEXT,
    container_40 TEXT,
    quant_container_20 INTEGER,
    quant_cont_40 INTEGER,
    contents TEXT,
    empresa TEXT,
    tipo_cliente TEXT,
    status_servico TEXT,
    avaliacao REAL,
    faturamento TEXT,
    fatura TEXT,
    coordenadora TEXT,
    equipe TEXT,
    anotacoes_servico TEXT,
    FOREIGN KEY (processo) REFERENCES Agenda(processo)
);
```

### 4. Tabela `Avaliacoes_Brutas`
Registra as notas e comentários das avaliações realizadas para cada processo.

```sql
CREATE TABLE Avaliacoes_Brutas (
    id_avaliacao INTEGER PRIMARY KEY AUTOINCREMENT,
    processo TEXT NOT NULL,
    data DATE,
    ano INTEGER,
    mes INTEGER,
    nota_pontualidade_coord REAL,
    nota_limpeza_embalagem REAL,
    nota_cortesia_carregamento REAL,
    nota_tecnica_cortesia REAL,
    comentario TEXT,
    FOREIGN KEY (processo) REFERENCES Agenda(processo)
);
```

### 5. VIEW `Comissoes_Calculadas`
Calcula a média simples das quatro notas de avaliação para cada processo. A fórmula utiliza `COALESCE` para tratar notas nulas como zero (por decisão de projeto, para não anular a média).

```sql
CREATE VIEW Comissoes_Calculadas AS
SELECT
    processo,
    (COALESCE(nota_pontualidade_coord,0) +
     COALESCE(nota_limpeza_embalagem,0) +
     COALESCE(nota_cortesia_carregamento,0) +
     COALESCE(nota_tecnica_cortesia,0)) / 4.0 AS media_avaliacao
FROM Avaliacoes_Brutas;
```

---

## Relacionamentos

- **Clientes** → **Agenda**: 1:N (um cliente pode ter vários processos).
- **Agenda** → **Servicos**: 1:N (um processo pode ter vários serviços).
- **Agenda** → **Avaliacoes_Brutas**: 1:N (um processo pode ter várias avaliações).

As chaves estrangeiras estão ativas via `PRAGMA foreign_keys = ON` para garantir a integridade referencial.

---

## Decisões de Normalização

- **Eliminação de redundâncias**: Os campos `volume`, `origem`, `destino`, `caixas`, `engradados` e `lifts` foram centralizados exclusivamente na tabela `Agenda`. A tabela `Servicos` **não** duplica essas informações.
- **Histórico de clientes**: Foi criado `id_cliente` autoincrementado para permitir que um mesmo cliente (com mesmo nome ou empresa) seja rastreado em diferentes processos, mesmo que os dados cadastrais mudem.
- **Status e anotações**: As tabelas `Agenda` e `Servicos` possuem seus próprios campos de status e anotações, com prefixos para evitar confusão (`status_agenda`, `anotacoes_agenda`, `status_servico`, `anotacoes_servico`).

---

## Importação de Dados Reais (Planilhas CSV)

### Pontos Críticos Identificados

1. **Datas inconsistentes**: Muitas células das colunas de data contêm textos como `"ASAP"`, `"19 e 20/01"` (faixas). Para esses casos, o valor será deixado em branco e o texto original será armazenado no campo `anotacoes_agenda` (ou campo similar) para não perder a informação.

2. **Falta de correspondência entre processos**: A planilha `agenda.CSV` contém processos recentes (2026, códigos 15000+), enquanto `servicos.CSV` e `avaliacao_bruta.CSV` contêm processos mais antigos (2024, códigos 13000+). Cerca de 85 dos 99 processos com avaliação não existem em `agenda.CSV`.  
   **Solução**: Para esses processos órfãos, será criada uma linha mínima na tabela `Agenda` contendo apenas o `processo` (e demais campos nulos), garantindo a integridade referencial e permitindo a associação com serviços e avaliações.

3. **Múltiplas linhas por OS**: Na planilha `servicos.CSV`, uma mesma `os` pode aparecer diversas vezes, representando diferentes pernas ou dias de execução.  
   **Solução**: Cada linha será mantida como um registro separado na tabela `Servicos` (granularidade por evento/dia), pois isso reflete a realidade operacional. A `os` deixa de ser um identificador único de serviço, mas é preservada como campo descritivo.

### Formato dos Arquivos

- Separador: `;`
- Codificação: `ISO-8859-1` (Latin-1) – o script de importação converterá para UTF-8 internamente.
- Números: vírgula como separador decimal (ex: `1,2`).
- Datas: majoritariamente no formato `dd/mm/aaaa`.

---

## Scripts Disponíveis

### `setup_db.py`

Script Python para criação do banco e carga de dados de teste (dummy). Principais funções:

- Cria o banco `mudancas_filial.db` (ou conecta-se a ele).
- Cria todas as tabelas e a VIEW.
- Insere dados de teste para validar o fluxo completo.
- Executa consultas de demonstração (JOIN entre Agenda e Servicos, SELECT na VIEW).
- Utiliza `pandas` para exibir os resultados.

**Como usar**:
```bash
python3 setup_db.py
```

O script é **idempotente**: pode ser executado múltiplas vezes sem gerar conflitos (os dados de teste são limpos antes da recriação).

### `importar_csv.py` (a ser desenvolvido)

Script que lerá os CSVs reais (agenda, servicos, avaliacao_bruta) e populará o banco aplicando as regras de negócio definidas (datas inconsistentes, processos órfãos, múltiplas linhas por OS). Este script ainda está em fase de planejamento.

---

## Codificação e Considerações Técnicas

- **Banco de dados**: SQLite 3.x, com encoding UTF-8 (confirmado pelo comando `file`). O arquivo `.db` é binário; não deve ser aberto como texto puro.
- **Visualização**: Utilize ferramentas como **DB Browser for SQLite** (`sudo apt install sqlitebrowser`), extensão SQLite no VS Code, ou o CLI do SQLite (`sqlite3 mudancas_filial.db`).
- **Python**: Biblioteca `sqlite3` (nativa) e `pandas` para manipulação de dados. Use `PRAGMA foreign_keys = ON` na conexão para ativar restrições de chave estrangeira.

---

## Próximos Passos

- Desenvolver o script de importação dos CSVs reais, tratando as inconsistências mapeadas.
- Expandir o cálculo de comissões a partir da VIEW, utilizando Python para gerar relatórios.
- Automatizar envio de e-mails com base no status dos processos e avaliações.
- Criar interfaces de consulta (Dashboards) usando pandas e/ou ferramentas de BI.

---

## Observações Finais

Este guia serve como referência única para o entendimento da estrutura e das regras de negócio do banco. Qualquer alteração no esquema ou nas regras deve ser documentada aqui para manter a consistência entre a equipe e as ferramentas (como o Claude Code).

--- 
*Última atualização: 29/07/2026*
```