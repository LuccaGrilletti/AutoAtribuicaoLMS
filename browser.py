"""Navegador com perfil persistente e medidas anti-detecção.

Port do padrão comprovado em ModernaCOREAutoCheck/src/browser.py: a página de
login (identity.modernacore.com) usa reCAPTCHA v3 com scoring comportamental,
então Chrome real + perfil persistente + stealth são necessários para o login
não ser bloqueado ou rebaixado.
"""

import random

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

import config

# Rotação de UA: score de reCAPTCHA v3 cai com UA estático ou desatualizado
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
]

# Mascara navigator.webdriver e artefatos do ChromeDriver detectados pelo reCAPTCHA
_STEALTH_INIT = """(() => {
    try { Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true }); } catch(_) {}
    ['cdc_adoQpoasnfa76pfcZLmcfl_Array',
     'cdc_adoQpoasnfa76pfcZLmcfl_Promise',
     'cdc_adoQpoasnfa76pfcZLmcfl_Symbol'].forEach(k => { try { delete window[k]; } catch(_) {} });
    try {
        const cores = [4, 8][Math.round(Math.random())];
        const mem   = [4, 8][Math.round(Math.random())];
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => cores });
        Object.defineProperty(navigator, 'deviceMemory',        { get: () => mem });
    } catch(_) {}
    try {
        const _origQuery = window.navigator.permissions.query.bind(navigator.permissions);
        window.navigator.permissions.query = (p) =>
            p.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : _origQuery(p);
    } catch(_) {}
})();"""

# Overlay de debug visual (cursor + teclado); injetado apenas quando headless=False
_DEBUG_OVERLAY = """(() => {
    function mount() {
        if (!document.body || document.getElementById('__dbg_cur__')) return;

        const cur = document.createElement('div');
        cur.id = '__dbg_cur__';
        cur.style.cssText = 'position:fixed;width:14px;height:14px;background:crimson;border-radius:50%;border:2px solid #fff;box-shadow:0 0 6px rgba(0,0,0,.7);pointer-events:none;z-index:2147483647;transform:translate(-50%,-50%);top:-20px;left:-20px;';
        document.body.appendChild(cur);
        document.addEventListener('mousemove', e => {
            cur.style.left = e.clientX + 'px';
            cur.style.top  = e.clientY + 'px';
        }, true);

        const kbd = document.createElement('div');
        kbd.id = '__dbg_kbd__';
        kbd.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.78);color:#39ff14;font:bold 16px monospace;padding:6px 18px;border-radius:8px;pointer-events:none;z-index:2147483647;min-width:160px;text-align:center;letter-spacing:1px;opacity:0;transition:opacity .2s;';
        document.body.appendChild(kbd);

        let timer;
        document.addEventListener('keydown', e => {
            const pwd = document.activeElement && document.activeElement.type === 'password';
            const k   = pwd ? '•' : (e.key.length === 1 ? e.key : '[' + e.key + ']');
            kbd.textContent = (kbd.textContent + k).slice(-24);
            kbd.style.opacity = '1';
            clearTimeout(timer);
            timer = setTimeout(() => {
                kbd.style.opacity = '0';
                setTimeout(() => { kbd.textContent = ''; }, 200);
            }, 2000);
        }, true);
    }
    document.readyState === 'loading'
        ? document.addEventListener('DOMContentLoaded', mount)
        : mount();
})();"""


async def criar_browser(headless=False):
    playwright = await async_playwright().start()
    ua = random.choice(_USER_AGENTS)
    contexto = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(config.DIR_PERFIL_NAVEGADOR),  # perfil persistente melhora o score do reCAPTCHA
        headless=headless,
        channel="chrome",  # Chrome real exigido; Chromium recebe score reCAPTCHA mais baixo
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--lang=pt-BR",
            "--no-default-browser-check",
            "--no-first-run",
            "--disable-infobars",
        ],
        user_agent=ua,
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        viewport={"width": 1366, "height": 768},
        geolocation={"latitude": -23.5505, "longitude": -46.6333},
        permissions=["geolocation"],
    )
    # sessão órfã (ex.: Ctrl+C na execução anterior) deixa cookie do identity em
    # estado que gera loop de redirect OIDC (ERR_TOO_MANY_REDIRECTS) — zera os
    # cookies mantendo histórico/fingerprint do perfil (score do reCAPTCHA)
    await contexto.clear_cookies()
    await contexto.add_init_script(_STEALTH_INIT)
    if not headless:
        await contexto.add_init_script(_DEBUG_OVERLAY)
    pagina = await contexto.new_page()
    await Stealth().apply_stealth_async(pagina)
    return playwright, contexto, pagina


async def fechar_browser(playwright, contexto):
    await contexto.close()
    await playwright.stop()
