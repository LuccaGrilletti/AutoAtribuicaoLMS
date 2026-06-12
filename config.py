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

# Timeouts (ms)
TIMEOUT_ELEMENTO = 30_000
TIMEOUT_NAVEGACAO = 60_000

# Diretórios de runtime
DIR_PERFIL_NAVEGADOR = BASE_DIR / "browser_profile"
DIR_LOGS = BASE_DIR / "logs"
DIR_ERROS = BASE_DIR / "errors"
