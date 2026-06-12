"""Orquestração da atribuição de conteúdos por turma.

Fluxo completo: login → coleta de turmas pendentes → para cada turma,
configura em lote os grupos ANUAL/BIMESTRAL, com log CSV em logs/,
screenshot de falha em errors/ e resumo final no console.

Use --limite-turmas/--limite-grupos para execuções controladas de validação.
"""

import argparse
import asyncio
import re
import sys
from datetime import datetime

from playwright.async_api import Page

import config
from browser import criar_browser, fechar_browser
from logger import LoggerCSV
from pages.config_batch_page import ConfigBatchPage
from pages.lista_turmas_page import ListaTurmasPage
from pages.login_page import LoginPage
from pages.turma_detalhe_page import TurmaDetalhePage


def parse_args():
    parser = argparse.ArgumentParser(description="Atribuição de conteúdos por turma no Moderna CORE LMS")
    parser.add_argument("--limite-turmas", type=int, default=None,
                        help="processa no máximo N turmas (para validação)")
    parser.add_argument("--limite-grupos", type=int, default=None,
                        help="processa no máximo N grupos por turma (para validação)")
    return parser.parse_args()


def _resumir_erro(excecao: Exception) -> str:
    """Achata e trunca a mensagem (erros do Playwright trazem call log extenso)."""
    return " ".join(str(excecao).split())[:300]


async def salvar_screenshot(pagina: Page, turma_nome: str, grupo: str) -> str | None:
    config.DIR_ERROS.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    sufixo = re.sub(r"[^\w\-]+", "_", f"{turma_nome}_{grupo}")[:80]
    caminho = config.DIR_ERROS / f"{ts}_{sufixo}.png"
    try:
        await pagina.screenshot(path=str(caminho), full_page=True)
        return str(caminho)
    except Exception:
        return None  # screenshot é melhor-esforço; não pode mascarar o erro original


async def _registrar_erro(pagina: Page, log: LoggerCSV, turma_nome: str,
                          grupo: str, excecao: Exception):
    detalhe = _resumir_erro(excecao)
    caminho = await salvar_screenshot(pagina, turma_nome, grupo)
    log.registrar(turma_nome, grupo, "erro", detalhe)
    print(f"  ERRO ({grupo}): {detalhe}")
    if caminho:
        print(f"  screenshot: {caminho}")


async def processar_turma(detalhe: TurmaDetalhePage, batch: ConfigBatchPage,
                          turma: dict, limite_grupos: int | None,
                          log: LoggerCSV) -> list[str]:
    """Configura os grupos pendentes de uma turma; retorna os status gerados.

    Qualquer erro é registrado (CSV + screenshot) e a turma é abandonada —
    a execução continua na próxima.
    """
    statuses: list[str] = []
    try:
        await detalhe.abrir(turma["href"])
        await detalhe.ir_aba_cursos()
    except Exception as e:
        await _registrar_erro(detalhe.pagina, log, turma["nome"], "-", e)
        return ["erro"]

    processados: list[str] = []
    while True:
        if limite_grupos and len(processados) >= limite_grupos:
            break
        # re-consulta os botões a cada iteração: o DOM re-renderiza após salvar
        try:
            grupos = await detalhe.listar_grupos()
        except Exception as e:
            await _registrar_erro(detalhe.pagina, log, turma["nome"], "-", e)
            statuses.append("erro")
            break
        restantes = [g for g in grupos if g["tipo"] not in processados]
        if not restantes:
            break

        grupo = restantes[0]
        print(f"  configurando grupo {grupo['tipo']}...")
        try:
            await detalhe.clicar_configurar(grupo["indice"])
            await batch.configurar(grupo["tipo"])
            processados.append(grupo["tipo"])
            log.registrar(turma["nome"], grupo["tipo"], "sucesso_lote")
            statuses.append("sucesso_lote")
            print(f"  grupo {grupo['tipo']}: sucesso (lote)")
            await detalhe.ir_aba_cursos()  # o salvar redireciona para /class/{uuid}
        except Exception as e:
            # estado da página é incerto após a falha — abandona a turma
            await _registrar_erro(detalhe.pagina, log, turma["nome"], grupo["tipo"], e)
            statuses.append("erro")
            break

    # segunda passada: cursos que continuam pendentes após o lote são
    # configurados individualmente via engrenagem (evita retrabalho/loop do lote)
    tentados_individual: set[str] = set()
    while True:
        pendentes_individuais = await detalhe.listar_pendentes_individuais()
        restantes_individuais = [p for p in pendentes_individuais if p["nome"] not in tentados_individual]
        if not restantes_individuais:
            break

        item = restantes_individuais[0]
        tentados_individual.add(item["nome"])
        print(f"  resolvendo individualmente: {item['nome']} ({item['tipo']})")
        try:
            await detalhe.clicar_engrenagem(item["indice"])
            await batch.configurar(item["tipo"])
            await detalhe.ir_aba_cursos()

            ainda_pendente = any(
                p["nome"] == item["nome"]
                for p in await detalhe.listar_pendentes_individuais()
            )
            if ainda_pendente:
                log.registrar(turma["nome"], item["tipo"], "pendente_persistente", item["nome"])
                statuses.append("pendente_persistente")
                print(f"  {item['nome']}: continua pendente mesmo após config individual")
            else:
                log.registrar(turma["nome"], item["tipo"], "sucesso_individual", item["nome"])
                statuses.append("sucesso_individual")
                print(f"  {item['nome']}: resolvido individualmente")
        except Exception as e:
            await _registrar_erro(detalhe.pagina, log, turma["nome"], item["tipo"], e)
            statuses.append("erro")

    if not statuses:
        log.registrar(turma["nome"], "-", "pulado", "sem grupos para configurar")
        statuses.append("pulado")
        print("  sem grupos para configurar (pulado)")
    return statuses


async def main():
    args = parse_args()

    if not config.LMS_USER or not config.LMS_PASS:
        print("ERRO: preencha LMS_USER e LMS_PASS no arquivo .env antes de executar.")
        sys.exit(1)

    log = LoggerCSV()
    print(f"Log CSV desta execução: {log.caminho}")

    print("Abrindo navegador...")
    playwright, contexto, pagina = await criar_browser(headless=config.HEADLESS)
    try:
        try:
            print("Fazendo login e navegando até a lista de turmas (Grupos)...")
            login = LoginPage(contexto, pagina)
            pagina_campus = await login.executar_fluxo_completo()
            print("Login OK — lista de turmas aberta.")

            print("Coletando turmas com pendência de configuração...")
            lista = ListaTurmasPage(pagina_campus)
            pendentes = await lista.coletar_pendentes()
        except Exception as e:
            # falha antes do loop de turmas: registra e encerra
            await salvar_screenshot(pagina, "login_ou_coleta", "-")
            print(f"ERRO fatal no login/coleta: {_resumir_erro(e)}")
            raise

        print(f"\n=== {len(pendentes)} turma(s) com pendência ===")
        for turma in pendentes:
            print(f"- {turma['nome']}  ->  {turma['href']}")

        if args.limite_turmas:
            pendentes = pendentes[: args.limite_turmas]

        totais = {"sucesso_lote": 0, "sucesso_individual": 0,
                  "pendente_persistente": 0, "erro": 0, "pulado": 0}
        detalhe = TurmaDetalhePage(pagina_campus)
        batch = ConfigBatchPage(pagina_campus)
        for i, turma in enumerate(pendentes, start=1):
            print(f"\n[{i}/{len(pendentes)}] Turma: {turma['nome']}")
            statuses = await processar_turma(detalhe, batch, turma, args.limite_grupos, log)
            for status in statuses:
                totais[status] += 1

        print(f"\n=== Resumo: {totais['sucesso_lote']} sucesso(s) em lote, "
              f"{totais['sucesso_individual']} sucesso(s) individual(is), "
              f"{totais['pendente_persistente']} pendente(s) persistente(s), "
              f"{totais['erro']} erro(s), {totais['pulado']} pulado(s) ===")
        print(f"Log CSV: {log.caminho}")
    finally:
        await fechar_browser(playwright, contexto)


if __name__ == "__main__":
    asyncio.run(main())
