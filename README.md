# AutoAtribuicaoLMS

Automação (Python + Playwright async) da atribuição de conteúdos por turma no
Moderna CORE LMS: loga como gestor, varre a lista de turmas (menu Grupos do
Campus admin), identifica turmas com pendência de configuração e preenche o
formulário "Configurar em lote" (escala, períodos, modelo) de cada grupo de
cursos (ANUAL e/ou BIMESTRAL).

## Setup

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env   # preencher LMS_USER e LMS_PASS
```

Pré-requisito: Google Chrome instalado (o script usa `channel="chrome"`; não é
necessário `playwright install`). O login usa perfil persistente
(`browser_profile/`) + stealth por causa do reCAPTCHA v3 da página de login.

## Execução

```powershell
.venv\Scripts\python main.py                                      # execução completa
.venv\Scripts\python main.py --limite-turmas 1 --limite-grupos 1  # validação controlada
```

Saídas: log CSV em `logs/` (turma, grupo, tipo, status, detalhe, timestamp) e
screenshots de falha em `errors/`.

## Estrutura

- `browser.py` — Chrome persistente + anti-detecção (port do ModernaCOREAutoCheck)
- `pages/login_page.py` — login → Lobby → Campus → menu Grupos
- `pages/lista_turmas_page.py` — coleta paginada das turmas pendentes
- `pages/turma_detalhe_page.py` — aba Cursos e botões "Configurar em lote" por grupo
- `pages/config_batch_page.py` — preenchimento e salvamento do formulário
- `main.py` — orquestração; `logger.py` — CSV; `config.py` — .env e constantes
