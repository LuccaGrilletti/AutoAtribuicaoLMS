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
Copy-Item .env.example .env   # preencher LMS_USER/LMS_PASS e as variáveis DB_*
```

Pré-requisitos:

- **Google Chrome** instalado (o script usa `channel="chrome"`; não é necessário
  `playwright install`). O login usa perfil persistente (`browser_profile/`) +
  stealth por causa do reCAPTCHA v3 da página de login.
- **PostgreSQL** acessível. Crie o banco e as tabelas uma vez rodando
  `sql/schema.sql` no Query Tool do pgAdmin4 (ou no `psql`) — ele usa metacomandos
  do psql (`\c`), então é um passo manual, o código nunca o executa. Configure as
  variáveis `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASS` no `.env`.

## Execução

```powershell
.venv\Scripts\python main.py                                      # execução completa
.venv\Scripts\python main.py --limite-turmas 1 --limite-grupos 1  # validação controlada
```

Saídas: persistência em PostgreSQL — uma linha por execução na tabela `execucoes`
(início/fim, usuário, filtro, status e totais) e uma linha por grupo/curso
processado em `resultados` (turma, grupo, tipo, status, detalhe, timestamp),
ligadas por `execucao_id`. Screenshots de falha ficam em `errors/`.

## Estrutura

- `browser.py` — Chrome persistente + anti-detecção (port do ModernaCOREAutoCheck)
- `pages/login_page.py` — login → Lobby → Campus → menu Grupos
- `pages/lista_turmas_page.py` — coleta paginada das turmas pendentes
- `pages/turma_detalhe_page.py` — aba Cursos e botões "Configurar em lote" por grupo
- `pages/config_batch_page.py` — preenchimento e salvamento do formulário
- `main.py` — orquestração; `repositorio.py` — persistência PostgreSQL
  (`execucoes` + `resultados`); `sql/schema.sql` — criação do banco/tabelas;
  `config.py` — `.env` e constantes
