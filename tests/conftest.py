"""Fixtures de infraestrutura para os testes.

Cria o banco atribuicao_db_test uma vez por sessão e limpa as tabelas
antes de cada teste para garantir isolamento total entre eles.
"""

import psycopg2
import pytest
import config

TEST_DB = "atribuicao_db_test"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS execucoes (
    id                         SERIAL PRIMARY KEY,
    timestamp_inicio           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    timestamp_fim              TIMESTAMPTZ,
    usuario_lms                VARCHAR(255),
    filtro                     VARCHAR(255),
    status                     VARCHAR(50),
    total_sucesso_lote         INT DEFAULT 0,
    total_sucesso_individual   INT DEFAULT 0,
    total_pendente_persistente INT DEFAULT 0,
    total_erro                 INT DEFAULT 0,
    total_pulado               INT DEFAULT 0
);
CREATE TABLE IF NOT EXISTS resultados (
    id          SERIAL PRIMARY KEY,
    execucao_id INT REFERENCES execucoes(id),
    turma       VARCHAR(255),
    grupo       VARCHAR(50),
    tipo        VARCHAR(50),
    status      VARCHAR(50),
    detalhe     TEXT,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def _conectar_admin():
    """Conexão ao banco padrão 'postgres' para operações de admin (CREATE/DROP DB)."""
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname="postgres",
        user=config.DB_USER,
        password=config.DB_PASS,
    )


def _conectar_teste():
    """Conexão ao banco de testes."""
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=TEST_DB,
        user=config.DB_USER,
        password=config.DB_PASS,
    )


@pytest.fixture(scope="session", autouse=True)
def banco_teste():
    """Cria o banco de testes antes da sessão e o destrói ao final.

    scope='session': roda uma vez para toda a bateria de testes.
    autouse=True: ativa automaticamente sem precisar declarar nos testes.
    """
    conn = _conectar_admin()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
        cur.execute(f"CREATE DATABASE {TEST_DB}")
    conn.close()

    conn = _conectar_teste()
    with conn.cursor() as cur:
        cur.execute(_SCHEMA)
    conn.commit()
    conn.close()

    yield  # testes rodam aqui

    conn = _conectar_admin()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
    conn.close()


@pytest.fixture(autouse=True)
def limpar_tabelas(banco_teste):
    """Trunca as tabelas antes de cada teste para isolamento completo.

    RESTART IDENTITY: reseta as sequences (IDs voltam a 1 em cada teste).
    CASCADE: garante que resultados é truncado antes de execucoes (FK).
    Roda automaticamente antes de qualquer fixture de teste.
    """
    conn = _conectar_teste()
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE TABLE resultados, execucoes RESTART IDENTITY CASCADE"
        )
    conn.commit()
    conn.close()