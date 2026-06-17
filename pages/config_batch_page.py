"""Formulário "Configurar em lote": escala, período(s) e modelo(s) de avaliação.

Regras de negócio do spec:
- Opções de combobox nunca são cacheadas — opções já usadas somem dos campos
  seguintes, então a lista é re-consultada a cada seleção.
- Escala e Modelo têm sempre 1 única opção disponível — seleção dinâmica,
  sem hardcode de texto.
- BIMESTRAL: o período é sempre a versão com asterisco (`Bimestre {n}*`);
  digita-se `*` no filtro do combobox antes de escolher.
"""

import asyncio

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeout

import config


class ConfigBatchPage:
    CONTROL = ".select-customizable__control"
    OPCAO = ".select-customizable__option"
    INPUT_FILTRO = ".select-customizable__input input"
    ESCALA = ".class-content-config-body__select"
    PERIODO = ".class-content-config-body__period-select"
    MODELO = ".class-content-config-body__model-select"
    BOTAO_SALVAR = 'button:has-text("Salvar")'
    TOAST_SUCESSO = "text=Atualização realizada com sucesso"

    def __init__(self, pagina: Page):
        self.pagina = pagina

    async def configurar(self, tipo: str):
        """Preenche e salva o formulário (lote ou individual — mesma estrutura)."""
        await self._preencher_escala()
        if tipo == "ANUAL":
            await self._preencher_anual()
        elif tipo == "BIMESTRAL":
            await self._preencher_bimestral()
        else:
            raise RuntimeError(f"Tipo de grupo desconhecido: {tipo}")
        await self._salvar()

    # ---------- campos ----------

    async def _preencher_escala(self):
        container = self.pagina.locator(f'{self.ESCALA}:has([title="Escala"])')
        if await container.count() == 0:
            container = self.pagina.locator(self.ESCALA)
        container = container.first

        # o campo carrega async com placeholder "..." — esperar o render
        controle = container.locator(self.CONTROL).first
        await controle.wait_for(state="visible", timeout=config.TIMEOUT_ELEMENTO)
        prazo = asyncio.get_running_loop().time() + config.TIMEOUT_ELEMENTO / 1000 #asyncio.get_event_loop().time()
        while (await controle.inner_text()).strip() == "...":
            if asyncio.get_running_loop().time() > prazo: #asyncio.get_event_loop().time()
                raise PlaywrightTimeout("Campo Escala não terminou de carregar (placeholder '...')")
            await asyncio.sleep(0.2)

        await self._selecionar(container, unica=True)

    async def _preencher_anual(self):
        periodos = self.pagina.locator(self.PERIODO)
        await periodos.first.wait_for(state="visible", timeout=config.TIMEOUT_ELEMENTO)
        await self._selecionar(periodos.first, prefixo="Anual")
        await self._selecionar(self.pagina.locator(self.MODELO).first, unica=True)

    async def _preencher_bimestral(self):
        periodos = self.pagina.locator(self.PERIODO)
        await periodos.first.wait_for(state="visible", timeout=config.TIMEOUT_ELEMENTO)
        total = await periodos.count()  # esperado: 4 (Bimestre 1-4)
        for i in range(total):
            n = i + 1
            # digitar '*' filtra as opções com asterisco; nunca usar a versão sem '*'
            await self._selecionar(periodos.nth(i), filtro="*", prefixo=f"Bimestre {n}*")
            await self._selecionar(self.pagina.locator(self.MODELO).nth(i), unica=True)

    # ---------- combobox ----------

    async def _selecionar(self, container: Locator, *, filtro: str | None = None,
                          prefixo: str | None = None, unica: bool = False) -> str:
        """Abre o combobox do container e clica numa opção.

        `unica=True` exige exatamente 1 opção disponível; senão usa a primeira
        opção cujo texto começa com `prefixo`. As opções são sempre
        re-consultadas após abrir/filtrar (nada de cache).
        """
        await container.locator(self.CONTROL).first.click()
        if filtro:
            campo = container.locator(self.INPUT_FILTRO)
            if await campo.count() == 0:
                campo = self.pagina.locator(self.INPUT_FILTRO).last
            else:
                campo = campo.first
            await campo.press_sequentially(filtro, delay=50)
            await asyncio.sleep(0.3)  # deixa o filtro re-renderizar as opções

        opcoes = self.pagina.locator(self.OPCAO)
        await opcoes.first.wait_for(state="visible", timeout=config.TIMEOUT_ELEMENTO)
        textos = [(await opcoes.nth(i).inner_text()).strip() for i in range(await opcoes.count())]

        if unica:
            if len(textos) != 1:
                raise RuntimeError(f"Esperava 1 única opção, encontrei {len(textos)}: {textos}")
            await opcoes.first.click()
            return textos[0]

        for i, texto in enumerate(textos):
            if texto.startswith(prefixo):
                await opcoes.nth(i).click()
                return texto
        raise RuntimeError(f"Nenhuma opção começa com '{prefixo}'; opções: {textos}")

    # ---------- salvar ----------

    async def _salvar(self):
        botao = self.pagina.locator(self.BOTAO_SALVAR).first
        await botao.wait_for(state="visible", timeout=config.TIMEOUT_ELEMENTO)
        # o botão só habilita com o form completo
        prazo = asyncio.get_running_loop().time() + config.TIMEOUT_ELEMENTO / 1000 #asyncio.get_event_loop().time()
        while await botao.is_disabled():
            if asyncio.get_running_loop().time() > prazo: #asyncio.get_event_loop().time()
                raise PlaywrightTimeout("Botão Salvar continuou desabilitado — formulário incompleto?")
            await asyncio.sleep(0.2)
        url_form = self.pagina.url
        await botao.click()

        # sucesso = toast + redirect; o toast pode sumir antes da checagem,
        # então a saída da URL do form (vale pro lote /config-batch e pro
        # individual /class/{turma}/config/{curso}) é a confirmação obrigatória
        try:
            await self.pagina.wait_for_selector(self.TOAST_SUCESSO, timeout=10_000)
        except PlaywrightTimeout:
            pass
        await self.pagina.wait_for_url(lambda url: url != url_form, timeout=20_000)
