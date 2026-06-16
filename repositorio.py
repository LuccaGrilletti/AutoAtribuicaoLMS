"""Persistência das execuções e resultados no PostgreSQL.

Padrão idêntico ao ModernaCOREAutoCheck: tabela `execucoes` (uma linha
por run do script) + tabela `resultados` (uma linha por grupo/curso
processado), relacionadas por execucao_id. Substituiu a persistência
anterior em CSV (`logger.py`), mantendo a assinatura de `registrar()`.

Cada insert em `resultados` é commitado imediatamente, então o registro
sobrevive a interrupções no meio do processo (ex.: Ctrl+C). A linha de
`execucoes` é aberta no __init__ e fechada com os totais em
`fechar_execucao()`, chamado no finally de main().
"""

import psycopg2

import config


class Repositorio:
    def __init__(self):
        self._conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASS,
        )
        self._conn.autocommit = False
        self.execucao_id: int = self._abrir_execucao()

    def _abrir_execucao(self) -> int:
        """Insere a linha de execução e retorna o id gerado."""
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO execucoes (usuario_lms, filtro)
                VALUES (%s, %s)
                RETURNING id
                """,
                (config.LMS_USER, config.TURMA_FILTRO or None),
            )
            execucao_id = cur.fetchone()[0]
        self._conn.commit()
        return execucao_id

    def registrar(self, turma: str, grupo: str, status: str, detalhe: str = ""):
        """Insere um resultado individual. Commit imediato — sobrevive a Ctrl+C.

        status ∈ {sucesso_lote, sucesso_individual, pendente_persistente, erro, pulado}
        grupo  ∈ {ANUAL, BIMESTRAL, -}
        """
        tipo = grupo.lower() if grupo in ("ANUAL", "BIMESTRAL") else ""
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO resultados
                    (execucao_id, turma, grupo, tipo, status, detalhe)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (self.execucao_id, turma, grupo, tipo, status, detalhe or None),
            )
        self._conn.commit()

    def fechar_execucao(self, totais: dict, status: str = "concluido"):
        """Atualiza a linha de execução com totais e timestamp de fim."""
        with self._conn.cursor() as cur:
            cur.execute(
                """
                UPDATE execucoes SET
                    timestamp_fim              = NOW(),
                    status                     = %s,
                    total_sucesso_lote         = %s,
                    total_sucesso_individual   = %s,
                    total_pendente_persistente = %s,
                    total_erro                 = %s,
                    total_pulado               = %s
                WHERE id = %s
                """,
                (
                    status,
                    totais.get("sucesso_lote", 0),
                    totais.get("sucesso_individual", 0),
                    totais.get("pendente_persistente", 0),
                    totais.get("erro", 0),
                    totais.get("pulado", 0),
                    self.execucao_id,
                ),
            )
        self._conn.commit()

    def fechar_conexao(self):
        """Fechar sempre no finally de main() — mesmo em caso de erro fatal."""
        try:
            self._conn.close()
        except Exception:
            pass
