"""Testes do Repositorio — persistência PostgreSQL.

Roda contra atribuicao_db_test (criado/destruído pelo conftest.py).
Cada teste começa com tabelas limpas (fixture limpar_tabelas no conftest).

Não usa mocks: testa o comportamento real contra o banco, incluindo
tipos PostgreSQL, commits imediatos e integridade referencial.
"""

import psycopg2
import pytest

import config
from main import _resumir_erro
from repositorio import Repositorio
from tests.conftest import TEST_DB


# ---------- helpers ----------


def _conn():
    """Conexão independente ao banco de testes para verificação pós-operação."""
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=TEST_DB,
        user=config.DB_USER,
        password=config.DB_PASS,
    )


def _buscar_execucao(execucao_id: int) -> dict:
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM execucoes WHERE id = %s", (execucao_id,))
        cols = [d[0] for d in cur.description]
        row = cur.fetchone()
    conn.close()
    return dict(zip(cols, row)) if row else {}


def _buscar_resultados(execucao_id: int) -> list[dict]:
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM resultados WHERE execucao_id = %s ORDER BY id",
            (execucao_id,),
        )
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


# ---------- fixture ----------


@pytest.fixture
def repo(monkeypatch):
    """Repositorio apontando para o banco de testes.

    monkeypatch garante que config.DB_NAME é restaurado após cada teste.
    """
    monkeypatch.setattr(config, "DB_NAME", TEST_DB)
    monkeypatch.setattr(config, "LMS_USER", "gestor_teste")
    monkeypatch.setattr(config, "TURMA_FILTRO", "")
    r = Repositorio()
    yield r
    r.fechar_conexao()


# ---------- testes: abrir execução ----------


class TestAbrirExecucao:
    def test_cria_exatamente_uma_linha_em_execucoes(self, repo):
        conn = _conn()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM execucoes")
            assert cur.fetchone()[0] == 1
        conn.close()

    def test_retorna_id_inteiro_positivo(self, repo):
        assert isinstance(repo.execucao_id, int)
        assert repo.execucao_id > 0

    def test_registra_usuario_lms_correto(self, repo):
        dados = _buscar_execucao(repo.execucao_id)
        assert dados["usuario_lms"] == "gestor_teste"

    def test_filtro_vazio_salvo_como_null(self, repo):
        dados = _buscar_execucao(repo.execucao_id)
        assert dados["filtro"] is None

    def test_filtro_preenchido_e_salvo(self, monkeypatch):
        monkeypatch.setattr(config, "DB_NAME", TEST_DB)
        monkeypatch.setattr(config, "LMS_USER", "gestor_teste")
        monkeypatch.setattr(config, "TURMA_FILTRO", "Turma G")
        r = Repositorio()
        dados = _buscar_execucao(r.execucao_id)
        r.fechar_conexao()
        assert dados["filtro"] == "Turma G"

    def test_timestamp_fim_inicia_como_null(self, repo):
        dados = _buscar_execucao(repo.execucao_id)
        assert dados["timestamp_fim"] is None

    def test_status_inicia_como_null(self, repo):
        dados = _buscar_execucao(repo.execucao_id)
        assert dados["status"] is None


# ---------- testes: registrar resultado ----------


class TestRegistrar:
    def test_insere_linha_em_resultados(self, repo):
        repo.registrar("1º ano EF AI Turma G - Matutino", "BIMESTRAL", "sucesso_lote")
        assert len(_buscar_resultados(repo.execucao_id)) == 1

    def test_tipo_anual_derivado_do_grupo(self, repo):
        repo.registrar("Turma X", "ANUAL", "sucesso_lote")
        assert _buscar_resultados(repo.execucao_id)[0]["tipo"] == "anual"

    def test_tipo_bimestral_derivado_do_grupo(self, repo):
        repo.registrar("Turma X", "BIMESTRAL", "sucesso_lote")
        assert _buscar_resultados(repo.execucao_id)[0]["tipo"] == "bimestral"

    def test_tipo_vazio_para_grupo_traco(self, repo):
        repo.registrar("Turma X", "-", "pulado")
        assert _buscar_resultados(repo.execucao_id)[0]["tipo"] == ""

    def test_detalhe_vazio_salvo_como_null(self, repo):
        repo.registrar("Turma X", "ANUAL", "sucesso_lote")
        assert _buscar_resultados(repo.execucao_id)[0]["detalhe"] is None

    def test_detalhe_preenchido_e_salvo(self, repo):
        repo.registrar("Turma X", "BIMESTRAL", "erro", "timeout ao clicar Salvar")
        assert _buscar_resultados(repo.execucao_id)[0]["detalhe"] == "timeout ao clicar Salvar"

    def test_commit_imediato_visivel_em_outra_conexao(self, repo):
        """Garante durabilidade: dado visível antes de fechar_execucao().

        Esta é a propriedade mais crítica do Repositorio — resultados devem
        sobreviver a um Ctrl+C entre registrar() e fechar_execucao().
        """
        repo.registrar("Turma Durabilidade", "ANUAL", "sucesso_lote", "verificacao")
        conn = _conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT detalhe FROM resultados WHERE turma = %s",
                ("Turma Durabilidade",),
            )
            row = cur.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "verificacao"

    def test_vincula_ao_execucao_id_correto(self, repo):
        repo.registrar("Turma Z", "BIMESTRAL", "erro", "timeout")
        resultado = _buscar_resultados(repo.execucao_id)[0]
        assert resultado["execucao_id"] == repo.execucao_id

    def test_multiplos_registros_na_mesma_execucao(self, repo):
        repo.registrar("Turma A", "ANUAL", "sucesso_lote")
        repo.registrar("Turma A", "BIMESTRAL", "sucesso_lote")
        repo.registrar("Turma B", "-", "pulado")
        resultados = _buscar_resultados(repo.execucao_id)
        assert len(resultados) == 3
        assert resultados[0]["turma"] == "Turma A"
        assert resultados[2]["status"] == "pulado"

    def test_todos_os_status_validos_sao_aceitos(self, repo):
        status_validos = [
            "sucesso_lote",
            "sucesso_individual",
            "pendente_persistente",
            "erro",
            "pulado",
        ]
        for status in status_validos:
            repo.registrar("Turma X", "ANUAL", status)
        resultados = _buscar_resultados(repo.execucao_id)
        assert [r["status"] for r in resultados] == status_validos


# ---------- testes: fechar execução ----------


class TestFecharExecucao:
    def test_atualiza_todos_os_totais(self, repo):
        totais = {
            "sucesso_lote": 5,
            "sucesso_individual": 2,
            "pendente_persistente": 1,
            "erro": 1,
            "pulado": 3,
        }
        repo.fechar_execucao(totais)
        dados = _buscar_execucao(repo.execucao_id)
        assert dados["total_sucesso_lote"] == 5
        assert dados["total_sucesso_individual"] == 2
        assert dados["total_pendente_persistente"] == 1
        assert dados["total_erro"] == 1
        assert dados["total_pulado"] == 3

    def test_status_padrao_e_concluido(self, repo):
        repo.fechar_execucao({})
        assert _buscar_execucao(repo.execucao_id)["status"] == "concluido"

    def test_status_erro_fatal_e_aceito(self, repo):
        repo.fechar_execucao({}, status="erro_fatal")
        assert _buscar_execucao(repo.execucao_id)["status"] == "erro_fatal"

    def test_grava_timestamp_fim(self, repo):
        repo.fechar_execucao({})
        assert _buscar_execucao(repo.execucao_id)["timestamp_fim"] is not None

    def test_dict_vazio_resulta_em_zeros(self, repo):
        repo.fechar_execucao({})
        dados = _buscar_execucao(repo.execucao_id)
        assert dados["total_sucesso_lote"] == 0
        assert dados["total_erro"] == 0

    def test_chaves_ausentes_no_dict_defaultam_para_zero(self, repo):
        repo.fechar_execucao({"sucesso_lote": 3})  # demais ausentes
        dados = _buscar_execucao(repo.execucao_id)
        assert dados["total_sucesso_lote"] == 3
        assert dados["total_erro"] == 0


# ---------- testes: fechar conexão ----------


class TestFecharConexao:
    def test_pode_ser_chamado_multiplas_vezes_sem_erro(self, repo):
        """fechar_conexao() é chamado no finally — deve ser idempotente."""
        repo.fechar_conexao()
        repo.fechar_conexao()  # segunda chamada não deve levantar exceção


# ---------- testes: _resumir_erro (main.py) ----------


class TestResumirErro:
    def test_trunca_mensagem_em_300_caracteres(self):
        erro = Exception("x" * 400)
        assert len(_resumir_erro(erro)) <= 300

    def test_achata_quebras_de_linha(self):
        erro = Exception("linha1\n  linha2\n    linha3")
        assert "\n" not in _resumir_erro(erro)

    def test_achata_espacos_multiplos(self):
        erro = Exception("erro    com    espacos    extras")
        resultado = _resumir_erro(erro)
        assert "    " not in resultado

    def test_mensagem_curta_nao_e_alterada(self):
        erro = Exception("erro simples")
        assert _resumir_erro(erro) == "erro simples"