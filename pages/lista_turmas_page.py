"""Lista de turmas (menu Grupos): coleta paginada das turmas com pendência."""

from playwright.async_api import Page

import config


class ListaTurmasPage:
    ROW = 'table[role="table"] tbody tr[role="row"]'
    LINK_TURMA = 'a[href^="/class/"]'
    NOME_TURMA = "span.title"
    INDICADOR_PENDENTE = '[aria-label*="Pendente"]'
    BOTAO_PROXIMA_PAGINA = 'button[aria-label="Go to next page"]'

    def __init__(self, pagina: Page):
        self.pagina = pagina

    async def coletar_pendentes(self) -> list[dict]:
        """Percorre todas as páginas da tabela e retorna [{"nome", "href"}] das
        turmas com indicador de pendência (deduplicado por href)."""
        pendentes: dict[str, dict] = {}
        numero_pagina = 1
        while True:
            await self.pagina.wait_for_selector(self.ROW, timeout=config.TIMEOUT_ELEMENTO)
            turmas_da_pagina = await self._coletar_pagina_atual()
            for turma in turmas_da_pagina:
                pendentes.setdefault(turma["href"], turma)
            print(f"  página {numero_pagina}: {len(turmas_da_pagina)} pendente(s)")
            if not await self._ir_para_proxima_pagina():
                break
            numero_pagina += 1

        turmas = list(pendentes.values())
        if config.TURMA_FILTRO:
            filtro = config.TURMA_FILTRO.lower()
            turmas = [t for t in turmas if filtro in t["nome"].lower()]
        return turmas

    async def _coletar_pagina_atual(self) -> list[dict]:
        turmas = []
        rows = self.pagina.locator(self.ROW)
        for i in range(await rows.count()):
            row = rows.nth(i)
            if await row.locator(self.INDICADOR_PENDENTE).count() == 0:
                continue
            links = row.locator(self.LINK_TURMA)
            if await links.count() == 0:
                continue
            link = links.first
            href = await link.get_attribute("href")
            nomes = row.locator(self.NOME_TURMA)
            if await nomes.count() > 0:
                nome = (await nomes.first.inner_text()).strip()
            else:
                nome = (await link.inner_text()).strip()
            turmas.append({"nome": nome, "href": href})
        return turmas

    async def _ir_para_proxima_pagina(self) -> bool:
        """Avança para a próxima página; False quando o botão está desabilitado."""
        botao = self.pagina.locator(self.BOTAO_PROXIMA_PAGINA)
        if await botao.count() == 0:
            return False
        if await botao.is_disabled() or (await botao.get_attribute("aria-disabled")) == "true":
            return False

        href_primeira = await self.pagina.locator(f"{self.ROW} {self.LINK_TURMA}").first.get_attribute("href")
        await botao.click()
        # tabela re-renderiza via SPA: espera a primeira linha mudar antes de re-ler
        await self.pagina.wait_for_function(
            """(hrefAnterior) => {
                const a = document.querySelector('table[role="table"] tbody tr[role="row"] a[href^="/class/"]');
                return a && a.getAttribute('href') !== hrefAnterior;
            }""",
            arg=href_primeira,
            timeout=config.TIMEOUT_ELEMENTO,
        )
        return True
