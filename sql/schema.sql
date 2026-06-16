-- Executar uma vez para criar o banco e as tabelas.
-- Conectar como superuser no psql ou no Query Tool do pgAdmin4.
-- Usa metacomandos do psql (\c) — é script manual; o código nunca o executa.

CREATE DATABASE atribuicao_db;

\c atribuicao_db

CREATE TABLE execucoes (
    id                         SERIAL PRIMARY KEY,
    timestamp_inicio           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    timestamp_fim              TIMESTAMPTZ,
    usuario_lms                VARCHAR(255),
    filtro                     VARCHAR(255),
    status                     VARCHAR(50),    -- 'concluido' | 'erro_fatal'
    total_sucesso_lote         INT DEFAULT 0,
    total_sucesso_individual   INT DEFAULT 0,
    total_pendente_persistente INT DEFAULT 0,
    total_erro                 INT DEFAULT 0,
    total_pulado               INT DEFAULT 0
);

CREATE TABLE resultados (
    id          SERIAL PRIMARY KEY,
    execucao_id INT REFERENCES execucoes(id),
    turma       VARCHAR(255),
    grupo       VARCHAR(50),    -- 'ANUAL' | 'BIMESTRAL' | '-'
    tipo        VARCHAR(50),    -- 'anual' | 'bimestral' | ''
    status      VARCHAR(50),    -- 'sucesso_lote' | 'sucesso_individual' |
                                --  'pendente_persistente' | 'erro' | 'pulado'
    detalhe     TEXT,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
