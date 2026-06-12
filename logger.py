"""Log CSV da execução: uma linha por grupo processado (ou turma pulada).

Cada execução cria um arquivo novo em logs/; as linhas são gravadas
imediatamente, então o log sobrevive a interrupções no meio da execução.
"""

import csv
from datetime import datetime

import config


class LoggerCSV:
    CAMPOS = ["turma", "grupo", "tipo", "status", "detalhe", "timestamp"]

    def __init__(self):
        config.DIR_LOGS.mkdir(exist_ok=True)
        nome = f"atribuicao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.caminho = config.DIR_LOGS / nome
        # utf-8-sig: BOM para o Excel abrir acentos corretamente no Windows
        with open(self.caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
            csv.writer(arquivo).writerow(self.CAMPOS)

    def registrar(self, turma: str, grupo: str, status: str, detalhe: str = ""):
        """status ∈ {sucesso_lote, sucesso_individual, pendente_persistente,
        erro, pulado}; grupo = ANUAL | BIMESTRAL | '-'."""
        tipo = grupo.lower() if grupo in ("ANUAL", "BIMESTRAL") else ""
        with open(self.caminho, "a", newline="", encoding="utf-8-sig") as arquivo:
            csv.writer(arquivo).writerow([
                turma, grupo, tipo, status, detalhe,
                datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            ])
