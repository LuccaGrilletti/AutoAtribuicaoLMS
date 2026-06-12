"""Detalhe da turma: aba Cursos e botões "Configurar em lote" por grupo.

Cada seção de grupo de cursos (ANUAL e/ou BIMESTRAL) tem um botão
`button.config-batch-button`; a seção é identificada pelo texto precedente,
pois o mesmo curso pode ser anual numa turma e bimestral noutra.
"""

import asyncio
import re
from urllib.parse import urlsplit

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

import config

# Caminha pelos irmãos anteriores (e sobe pelos ancestrais) do botão até achar
# o texto do cabeçalho da seção — o match mais próximo do botão vence.
_JS_TIPO_SECAO = """el => {
    const regex = /\\b(ANUAL|BIMESTRAL)\\b/i;
    let node = el;
    while (node) {
        let irmao = node.previousElementSibling;
        while (irmao) {
            const m = (irmao.textContent || '').match(regex);
            if (m) return m[1].toUpperCase();
            irmao = irmao.previousElementSibling;
        }
        node = node.parentElement;
    }
    return null;
}"""


class TurmaDetalhePage:
    BOTAO_CONFIG_LOTE = "button.config-batch-button"
    ABA_CURSOS_FALLBACK = 'text="Cursos"'

    def __init__(self, pagina: Page):
        self.pagina = pagina

    async def abrir(self, href: str):
        """Navega direto para a página da turma (href coletado na lista)."""
        partes = urlsplit(self.pagina.url)
        origem = f"{partes.scheme}://{partes.netloc}"
        await self.pagina.goto(origem + href, wait_until="domcontentloaded",
                               timeout=config.TIMEOUT_NAVEGACAO)

    async def ir_aba_cursos(self):
        """Abre a aba Cursos (texto igual em PT e ES)."""
        aba = self.pagina.get_by_role("tab", name=re.compile("cursos", re.I))
        try:
            await aba.first.click(timeout=10_000)
        except Exception:
            await self.pagina.click(self.ABA_CURSOS_FALLBACK, timeout=config.TIMEOUT_ELEMENTO)
        await asyncio.sleep(1.5)  # conteúdo da aba renderiza via SPA

    async def listar_grupos(self) -> list[dict]:
        """Retorna [{"tipo", "indice"}] dos botões "Configurar em lote" presentes.

        Lista vazia = nada a configurar nesta turma (status "pulado").
        """
        botoes = self.pagina.locator(self.BOTAO_CONFIG_LOTE)
        try:
            await botoes.first.wait_for(state="visible", timeout=10_000)
        except PlaywrightTimeout:
            return []
        grupos = []
        for i in range(await botoes.count()):
            tipo = await botoes.nth(i).evaluate(_JS_TIPO_SECAO)
            grupos.append({"tipo": (tipo or "DESCONHECIDO").upper(), "indice": i})
        return grupos

    async def clicar_configurar(self, indice: int):
        """Clica no botão "Configurar em lote" da seção e espera o formulário abrir."""
        await self.pagina.locator(self.BOTAO_CONFIG_LOTE).nth(indice).click()
        await self.pagina.wait_for_url("**config-batch**", timeout=config.TIMEOUT_NAVEGACAO)
