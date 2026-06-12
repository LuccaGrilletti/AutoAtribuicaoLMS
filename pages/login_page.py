"""Login e navegação inicial: identity → Lobby → Campus → menu Grupos.

A digitação humanizada, os movimentos de mouse e o aquecimento via Google
existem para o scoring comportamental do reCAPTCHA v3 da página de login
(padrão portado do ModernaCOREAutoCheck).
"""

import asyncio
import random

from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth

import config


class LoginPage:
    CAMPO_USUARIO = "#id_username"
    CAMPO_SENHA = "#id_password"
    BOTAO_ENTRAR = "#loginBtn"
    ERRO_LOGIN = "#error-messages p"
    # card do lobby: seletor do AutoCheck com fallback no [title="Campus"] (img dentro do card)
    CARD_CAMPUS = 'div.card:has(img[title="Campus"]), [title="Campus"]'
    MENU_GRUPOS = '[aria-label="Grupos"]'
    ROW_TURMA = 'table[role="table"] tbody tr[role="row"]'

    def __init__(self, contexto: BrowserContext, pagina: Page):
        self.contexto = contexto
        self.pagina = pagina

    # ---------- helpers de humanização (anti-reCAPTCHA) ----------

    async def _digitar_humanizado(self, seletor: str, texto: str):
        # delays e hesitações por caractere simulam cadência humana
        await self.pagina.click(seletor)
        for caractere in texto:
            await self.pagina.type(seletor, caractere, delay=random.randint(80, 180))
            if random.random() < 0.2:
                await asyncio.sleep(random.uniform(0.3, 0.8))
            else:
                await asyncio.sleep(random.uniform(0.01, 0.05))

    async def _mover_mouse_aleatorio(self, passos: int = 3):
        for _ in range(passos):
            x = random.randint(100, 1266)
            y = random.randint(100, 668)
            await self.pagina.mouse.move(x, y, steps=random.randint(8, 15))
            await asyncio.sleep(random.uniform(0.2, 0.5))

    async def _aquecer_sessao(self):
        # visita ao Google sinaliza ao reCAPTCHA uma sessão de navegação real
        await self.pagina.goto("https://www.google.com.br")
        await asyncio.sleep(random.uniform(2.0, 4.0))
        await self.pagina.mouse.wheel(0, random.randint(100, 300))
        await asyncio.sleep(random.uniform(1.0, 2.0))

    async def _ler_erro_login(self) -> str:
        try:
            elemento = await self.pagina.wait_for_selector(self.ERRO_LOGIN, timeout=3000)
            return (await elemento.inner_text()).strip()
        except Exception:
            return "Login não concluído — motivo desconhecido"

    # ---------- fluxo ----------

    async def fazer_login(self):
        """Abre o lobby (redireciona ao identity) e faz o login do gestor."""
        await self._aquecer_sessao()
        await self.pagina.goto(config.LOBBY_URL)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        await self._mover_mouse_aleatorio(passos=random.randint(2, 4))

        await self._digitar_humanizado(self.CAMPO_USUARIO, config.LMS_USER)
        await asyncio.sleep(random.uniform(0.5, 1.2))
        await self._digitar_humanizado(self.CAMPO_SENHA, config.LMS_PASS)
        await asyncio.sleep(random.uniform(0.8, 1.5))

        botao = await self.pagina.wait_for_selector(self.BOTAO_ENTRAR, timeout=config.TIMEOUT_ELEMENTO)
        caixa = await botao.bounding_box()
        centro_x = caixa["x"] + caixa["width"] / 2
        centro_y = caixa["y"] + caixa["height"] / 2
        await self.pagina.mouse.move(centro_x, centro_y, steps=20)
        await asyncio.sleep(random.uniform(0.3, 0.7))
        async with self.pagina.expect_navigation(wait_until="domcontentloaded", timeout=config.TIMEOUT_NAVEGACAO):
            await self.pagina.mouse.click(centro_x, centro_y)

        if "/login" in self.pagina.url:
            raise RuntimeError(f"Falha no login: {await self._ler_erro_login()}")

    async def abrir_campus(self) -> Page:
        """Clica no card Campus do lobby e retorna a página do app Campus.

        No AutoCheck o card abre em nova aba; mantém fallback para mesma aba.
        """
        await self.pagina.wait_for_selector(self.CARD_CAMPUS, timeout=config.TIMEOUT_ELEMENTO)
        try:
            async with self.contexto.expect_page(timeout=15_000) as nova_pagina_info:
                await self.pagina.locator(self.CARD_CAMPUS).first.click()
            pagina_campus = await nova_pagina_info.value
        except PlaywrightTimeout:
            pagina_campus = self.pagina  # abriu na mesma aba

        await Stealth().apply_stealth_async(pagina_campus)
        await pagina_campus.wait_for_url("**adminescuela**", timeout=config.TIMEOUT_NAVEGACAO)
        await pagina_campus.wait_for_load_state("domcontentloaded")
        return pagina_campus

    async def ir_para_grupos(self, pagina_campus: Page):
        """Abre a lista de turmas pelo ícone Grupos do menu lateral."""
        await pagina_campus.click(self.MENU_GRUPOS, timeout=config.TIMEOUT_ELEMENTO)
        await pagina_campus.wait_for_selector(self.ROW_TURMA, timeout=config.TIMEOUT_ELEMENTO)

    async def executar_fluxo_completo(self) -> Page:
        """Login → Campus → Grupos; retorna a página do Campus na lista de turmas."""
        await self.fazer_login()
        pagina_campus = await self.abrir_campus()
        await self.ir_para_grupos(pagina_campus)
        return pagina_campus
