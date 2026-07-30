-- =====================================================================
-- SCHEMA: mudancas_filial.db
-- Banco relacional para controle de mudanças internacionais
-- Substitui o sistema legado em Microsoft Access
-- =====================================================================

-- Garante que as constraints de chave estrangeira sejam respeitadas
-- (no SQLite isso vem desligado por padrão em cada nova conexão)
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Tabela: Clientes
-- Guarda o histórico cadastral. Um mesmo cliente (nome/e-mail) pode
-- aparecer em várias linhas ao longo do tempo, uma por processo novo.
-- id_cliente é o identificador técnico (autoincremento), processo é
-- o vínculo com a mudança específica em si (Agenda).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Clientes (
    id_cliente     INTEGER PRIMARY KEY AUTOINCREMENT,
    processo       TEXT,
    nome_cliente   TEXT NOT NULL,
    email          TEXT,
    email_agendor  TEXT,
    agente         TEXT,
    empresa        TEXT,
    FOREIGN KEY (processo) REFERENCES Agenda(processo)
);

-- ---------------------------------------------------------------------
-- Tabela: Agenda
-- É a "raiz" de cada mudança. O processo nasce aqui e é usado como
-- chave primária unificadora para todas as outras tabelas.
-- Todos os dados de volumetria (volume, caixas, engradados, lifts)
-- e de origem/destino ficam exclusivamente aqui, sem duplicação em
-- Servicos.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Agenda (
    processo          TEXT PRIMARY KEY,
    recebido_em       DATE,
    data_a_inicial    DATE,
    data_b_inicial    DATE,
    data_a_ofertada   DATE,
    data_b_ofertada   DATE,
    volume            REAL,
    engradados        INTEGER,
    caixas            INTEGER,
    lifts             INTEGER,
    tipo              TEXT,
    status_agenda     TEXT,
    origem            TEXT,
    destino           TEXT,
    anotacoes_agenda  TEXT
);

-- ---------------------------------------------------------------------
-- Tabela: Servicos
-- Detalhamento operacional de cada processo (pode haver múltiplos
-- serviços/etapas por processo, por isso id_servico é autoincremento
-- e processo é apenas FK, não PK).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Servicos (
    id_servico              INTEGER PRIMARY KEY AUTOINCREMENT,
    processo                TEXT NOT NULL,
    servicos                TEXT,
    modal                   TEXT,
    os                      TEXT,
    ref_externa             TEXT,
    cidade                  TEXT,
    data_inicio             DATE,
    data_final              DATE,
    m3_real                 REAL,
    quant_itens             INTEGER,
    peso_kg                 REAL,
    peso_bruto              REAL,
    peso_bruto_real_1       REAL,
    peso_liquido            REAL,
    peso_liquido_real_1     REAL,
    etd                     DATE,
    eta                     DATE,
    liftvan                 TEXT,
    peso_liftvan            REAL,
    tara_liftvan            REAL,
    icamento                TEXT,
    container_20            TEXT,
    container_40            TEXT,
    quant_container_20      INTEGER,
    quant_cont_40           INTEGER,
    contents                TEXT,
    empresa                 TEXT,
    tipo_cliente            TEXT,
    status_servico          TEXT,
    faturamento             TEXT,
    fatura                  TEXT,
    coordenadora             TEXT,
    anotacoes_servico       TEXT,
    FOREIGN KEY (processo) REFERENCES Agenda(processo)
);

-- ---------------------------------------------------------------------
-- Tabela: Colaboradores
-- Cadastro único de cada pessoa que pode ser escalada em uma equipe de
-- serviço. Um mesmo colaborador participa de vários serviços ao longo
-- do tempo — por isso o cadastro é separado (não repetido como texto).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Colaboradores (
    id_colaborador    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_colaborador  TEXT NOT NULL UNIQUE
);

-- ---------------------------------------------------------------------
-- Tabela: Servico_Equipe
-- Tabela de ligação (muitos-para-muitos) entre Servicos e Colaboradores.
-- Substitui o antigo campo de texto "equipe" em Servicos: em vez de uma
-- lista solta numa célula, cada linha aqui é "esta pessoa participou
-- deste serviço". A ordem dos colaboradores nunca importa nesse modelo,
-- exatamente como descrito na regra de negócio.
-- A chave primária composta (id_servico, id_colaborador) impede que a
-- mesma pessoa seja adicionada duas vezes ao mesmo serviço.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Servico_Equipe (
    id_servico      INTEGER NOT NULL,
    id_colaborador  INTEGER NOT NULL,
    PRIMARY KEY (id_servico, id_colaborador),
    FOREIGN KEY (id_servico) REFERENCES Servicos(id_servico),
    FOREIGN KEY (id_colaborador) REFERENCES Colaboradores(id_colaborador)
);

-- ---------------------------------------------------------------------
-- Tabela: Avaliacoes_Brutas
-- Guarda as notas "cruas" de avaliação de qualidade do serviço,
-- uma linha por avaliação recebida. A VIEW Comissoes_Calculadas
-- (abaixo) resume isso por processo.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Avaliacoes_Brutas (
    id_avaliacao                  INTEGER PRIMARY KEY AUTOINCREMENT,
    processo                      TEXT NOT NULL,
    data                          DATE,
    ano                           INTEGER,
    mes                           INTEGER,
    nota_pontualidade_coord       REAL,
    nota_limpeza_embalagem        REAL,
    nota_cortesia_carregamento    REAL,
    nota_tecnica_cortesia         REAL,
    comentario                    TEXT,
    FOREIGN KEY (processo) REFERENCES Agenda(processo)
);

-- ---------------------------------------------------------------------
-- VIEW: Comissoes_Calculadas
-- Calcula a média simples das 4 notas de avaliação, agrupada por
-- processo. Uma VIEW não guarda dados fisicamente: ela roda essa
-- consulta toda vez que é referenciada, então está sempre atualizada
-- em relação a Avaliacoes_Brutas.
-- ---------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS Comissoes_Calculadas AS
SELECT
    processo,
    COUNT(*) AS qtd_avaliacoes,
    AVG(
        (
            COALESCE(nota_pontualidade_coord, 0) +
            COALESCE(nota_limpeza_embalagem, 0) +
            COALESCE(nota_cortesia_carregamento, 0) +
            COALESCE(nota_tecnica_cortesia, 0)
        ) / 4.0
    ) AS media_avaliacao
FROM Avaliacoes_Brutas
GROUP BY processo;
