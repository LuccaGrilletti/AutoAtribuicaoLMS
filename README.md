# AutoAtribuicaoLMS

Automação (Python + Playwright async) da atribuição de conteúdos por turma no
Moderna CORE LMS: loga como gestor, varre a lista de turmas (menu Grupos do
Campus admin), identifica turmas com pendência de configuração e preenche o
formulário "Configurar em lote" (escala, períodos, modelo) de cada grupo de
cursos (ANUAL e/ou BIMESTRAL).

## Sumário

- [Pré-requisitos](#pré-requisitos)
- [Guia do zero: clonar, configurar e rodar](#guia-do-zero-clonar-configurar-e-rodar)
- [Variáveis do `.env`](#variáveis-do-env)
- [Execução](#execução)
- [Saídas e resultados](#saídas-e-resultados)
- [Solução de problemas](#solução-de-problemas)
- [Estrutura do projeto](#estrutura-do-projeto)

## Pré-requisitos

Antes de começar, garanta que os itens abaixo estão instalados na máquina:

- **Git** — para clonar o repositório.
- **Python 3.10 ou superior** — o código usa sintaxe moderna de type hints
  (`str | None`). Confirme com `py --version` (Windows) ou `python3 --version`.
- **Google Chrome** instalado. O script usa `channel="chrome"`, então **não** é
  necessário rodar `playwright install` — ele reaproveita o Chrome do sistema.
  O login usa um perfil persistente (`browser_profile/`, criado automaticamente)
  + stealth por causa do reCAPTCHA v3 da página de login.
- **PostgreSQL** acessível (local ou remoto), com um usuário que possa criar
  banco e tabelas. Instale o servidor + pgAdmin4 (ou tenha o `psql` disponível).
- **Credenciais de gestor** do Moderna CORE LMS (usuário e senha).

> Os comandos deste guia são para **Windows + PowerShell** (ambiente alvo do
> projeto). Em Linux/macOS, troque `py` por `python3` e
> `.venv\Scripts\python` por `.venv/bin/python`.

## Guia do zero: clonar, configurar e rodar

Siga os passos na ordem. Ao final você terá o projeto rodando localmente.

### 1. Clonar o repositório

```powershell
git clone https://github.com/LuccaGrilletti/AutoAtribuicaoLMS.git
cd AutoAtribuicaoLMS
```

### 2. Criar o ambiente virtual e instalar as dependências

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
```

Isso instala Playwright, playwright-stealth, python-dotenv e psycopg2-binary
dentro de `.venv/` (sem sujar o Python global). Como o script usa o Chrome do
sistema, **não** rode `playwright install`.

### 3. Criar o banco e as tabelas no PostgreSQL

O arquivo `sql/schema.sql` cria o banco `atribuicao_db` e as tabelas
`execucoes` e `resultados`. Ele usa metacomandos do `psql` (`\c`), então é um
**passo manual** — o código nunca o executa.

Escolha **uma** das opções abaixo:

- **pgAdmin4:** abra o Query Tool conectado ao seu servidor (como superusuário,
  ex.: `postgres`), cole o conteúdo de `sql/schema.sql` e execute.
- **psql (linha de comando):**

  ```powershell
  psql -U postgres -f sql/schema.sql
  ```

Se o banco `atribuicao_db` já existir e você quiser recriá-lo do zero, apague-o
antes (`DROP DATABASE atribuicao_db;`) — o script não sobrescreve banco
existente.

### 4. Configurar as variáveis de ambiente (`.env`)

Copie o exemplo e edite o `.env` com suas credenciais:

```powershell
Copy-Item .env.example .env
notepad .env
```

Preencha **obrigatoriamente** `LMS_USER` e `LMS_PASS` (sem eles a execução
aborta) e ajuste as variáveis `DB_*` para apontar ao banco criado no passo 3.
Veja a tabela em [Variáveis do `.env`](#variáveis-do-env).

### 5. Rodar uma validação controlada (recomendado no primeiro uso)

Antes de processar tudo, rode com limites baixos para conferir que login, banco
e preenchimento funcionam:

```powershell
.venv\Scripts\python main.py --limite-turmas 1 --limite-grupos 1
```

Deixe `HEADLESS=false` no `.env` neste primeiro teste para acompanhar o
navegador na tela. Se aparecer "Login OK" e uma linha for gravada na tabela
`execucoes`, está tudo certo.

### 6. Rodar a execução completa

```powershell
.venv\Scripts\python main.py
```

## Variáveis do `.env`

| Variável        | Obrigatória | Padrão                                   | Descrição |
|-----------------|-------------|------------------------------------------|-----------|
| `LMS_USER`      | **Sim**     | —                                        | Usuário (gestor) do Moderna CORE LMS. |
| `LMS_PASS`      | **Sim**     | —                                        | Senha do usuário. |
| `LOBBY_URL`     | Não         | `http://edi-modernacore.stn-neds.com`    | URL inicial (Lobby) do LMS. |
| `TURMA_FILTRO`  | Não         | *(vazio = todas)*                        | Filtra turmas por substring do nome. |
| `HEADLESS`      | Não         | `false`                                  | `true` roda sem abrir a janela do navegador. |
| `DB_HOST`       | Não         | `localhost`                              | Host do PostgreSQL. |
| `DB_PORT`       | Não         | `5432`                                   | Porta do PostgreSQL. |
| `DB_NAME`       | Não         | `atribuicao_db`                          | Nome do banco (criado pelo `schema.sql`). |
| `DB_USER`       | Não         | `postgres`                               | Usuário do banco. |
| `DB_PASS`       | Não         | `12345`                                  | Senha do banco. |

## Execução

```powershell
.venv\Scripts\python main.py                                      # execução completa
.venv\Scripts\python main.py --limite-turmas 1 --limite-grupos 1  # validação controlada
```

Flags de validação (opcionais):

- `--limite-turmas N` — processa no máximo **N** turmas.
- `--limite-grupos N` — processa no máximo **N** grupos por turma.

## Saídas e resultados

A persistência é toda em **PostgreSQL**:

- Tabela `execucoes` — uma linha por execução (início/fim, usuário, filtro,
  status e totais).
- Tabela `resultados` — uma linha por grupo/curso processado (turma, grupo,
  tipo, status, detalhe, timestamp), ligada por `execucao_id`.

Screenshots de falha ficam na pasta `errors/` (criada automaticamente).

## Solução de problemas

- **`ERRO: preencha LMS_USER e LMS_PASS no arquivo .env`** — o `.env` não existe
  ou está sem credenciais. Refaça o passo 4.
- **Erro de conexão com o banco** (`psycopg2.OperationalError`) — confira se o
  PostgreSQL está rodando e se as variáveis `DB_*` no `.env` batem com o
  servidor. Confirme também que o `schema.sql` foi executado (passo 3).
- **`database "atribuicao_db" does not exist`** — você pulou o passo 3; rode o
  `sql/schema.sql`.
- **Navegador não abre / falha ao iniciar** — confirme que o **Google Chrome**
  está instalado (o script usa `channel="chrome"`).
- **Falha/loop no login (reCAPTCHA)** — apague a pasta `browser_profile/` para
  resetar o perfil persistente e rode novamente com `HEADLESS=false`.

## Estrutura do projeto

- `browser.py` — Chrome persistente + anti-detecção (port do ModernaCOREAutoCheck)
- `pages/login_page.py` — login → Lobby → Campus → menu Grupos
- `pages/lista_turmas_page.py` — coleta paginada das turmas pendentes
- `pages/turma_detalhe_page.py` — aba Cursos e botões "Configurar em lote" por grupo
- `pages/config_batch_page.py` — preenchimento e salvamento do formulário
- `main.py` — orquestração; `repositorio.py` — persistência PostgreSQL
  (`execucoes` + `resultados`); `sql/schema.sql` — criação do banco/tabelas;
  `config.py` — `.env` e constantes
