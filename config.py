"""Configuração do projeto: variáveis do .env e constantes de execução."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

LOBBY_URL = os.getenv("LOBBY_URL", "http://edi-modernacore.stn-neds.com")
LMS_USER = os.getenv("LMS_USER", "").strip()
LMS_PASS = os.getenv("LMS_PASS", "").strip()
TURMA_FILTRO = os.getenv("TURMA_FILTRO", "").strip()
HEADLESS = os.getenv("HEADLESS", "false").strip().lower() in ("true", "1", "sim")

# Banco de dados
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "atribuicao_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "12345")

# Timeouts (ms)
TIMEOUT_ELEMENTO = 30_000
TIMEOUT_NAVEGACAO = 60_000

# Diretórios de runtime (resultados vão para o PostgreSQL, não para disco)
DIR_PERFIL_NAVEGADOR = BASE_DIR / "browser_profile"
DIR_ERROS = BASE_DIR / "errors"
