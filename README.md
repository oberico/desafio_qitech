# RNV — Instituição de Pagamento com Conta PJ

Instituição de pagamento que movimenta dinheiro de terceiros via gateway agnóstico. Não oferecemos crédito — apenas gerenciamos contas e transferências de forma segura e auditável.

**Desafio do Bootcamp QI Tech** · Monorepo com dois serviços independentes: `banco/` (ledger e autenticação) e `transferencias/` (orquestração de pagamentos).

---

## Quickstart — Rodar Localmente

### Pré-requisitos

- Docker & Docker Compose
- Python 3.11.x (a versão do projeto está em `.python-version`: 3.11.16). Necessário para rodar os testes na sua máquina.

### Primeira vez, passo a passo

**1. Clonar o repositório e entrar na raiz**

```bash
git clone <url-do-repositorio>
cd desafio_qitech
```

**2. Criar e ativar o venv — um único, na raiz**

O projeto tem **um único venv**, em `desafio_qitech/.venv`, e ele serve aos **dois** serviços. **Não crie venv dentro de `banco/` nem de `transferencias/`.**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

No Windows, a ativação muda:

```powershell
# PowerShell
.venv\Scripts\Activate.ps1

# cmd
.venv\Scripts\activate.bat
```

Confirme que ativou:
- o prompt mostra `(.venv)` no começo;
- `which python` (Mac/Linux) ou `where python` (Windows) aponta para dentro do `.venv` da raiz.

O `requirements-dev.txt` da raiz instala `banco/requirements.txt` + `transferencias/requirements.txt` (mesmas versões nos dois) + `pytest`. Os `requirements*.txt` dentro de `banco/` e `transferencias/` existem para o Docker (cada imagem cria seu próprio venv isolado em `/opt/venv`) e para o CI — você não precisa mexer neles. No Mac ARM, o `psycopg2-binary==2.9.10` já está fixado; não altere.

**3. Levantar os serviços**

```bash
docker compose up -d
```

Os containers são **efêmeros** (veja [Containers efêmeros](#containers-efêmeros-como-atualizar)): o `up -d` sempre reconstrói as imagens (`pull_policy: build`), então **não precisa de `--build`**. A primeira vez demora (build das imagens); nas próximas, o cache de camadas do Docker deixa o build rápido (~8 s sem mudanças). Isso levanta 4 containers:
- **banco-db** (PostgreSQL na porta 5434)
- **banco-api** (FastAPI na porta 8001)
- **transferencias-db** (PostgreSQL na porta 5433)
- **transferencias-api** (FastAPI na porta 8002)

Espere os 4 ficarem `healthy` (confira com `docker compose ps`, leva ~30 s). O `.env` é opcional (há defaults); se quiser personalizar, copie o `.env.example`.

**4. Conferir o health check** (veja abaixo)

**5. Rodar os testes** com `pytest` na **raiz**, com o venv ativo (veja [Como Testar](#como-testar)).

Mudou o schema (`database.sql`) ou quer o banco limpo: `docker compose down && docker compose up -d`. Os bancos não têm volume, então o `up` recria tudo do zero.

### Containers efêmeros: como atualizar

O compose **não monta volumes**: o código fica dentro da imagem e a API não roda com `--reload`. Editar `src/` no computador **não muda** o que o container serve até a imagem ser reconstruída, e `docker compose up -d` faz isso sempre. Os dois bancos usam `tmpfs` em `/var/lib/postgresql/data`: os dados vivem só na vida do container (na RAM, o que é irrelevante para este volume). A cada banco novo, o `database.sql` roda de novo, com o seed dos enumeradores e de `payment_method` (`pix`/`boleto`/`card`).

| Situação | Comando |
|----------|---------|
| Mudei código e quero manter os dados dos bancos | `docker compose up -d` (reconstrói e recria só o que mudou) |
| Quero tudo do zero (imagem nova + bancos vazios) | `docker compose down && docker compose up -d` |
| Reiniciar só uma API, mantendo o banco | `docker compose restart transferencias-api` (ou `banco-api`) |
| Ver logs | `docker compose logs -f banco-api` (ou `transferencias-api`) |

Avisos:

- `restart` **não reconstrói a imagem**: para pegar código novo, use `docker compose up -d`.
- `docker compose restart <db>` e `docker compose stop`/`start` **também zeram o banco** (o `tmpfs` some quando o container para). Para reiniciar só uma API sem perder dados, reinicie a API, nunca o banco.
- Nunca é preciso `down -v` (não há volume) nem `--build`.

Fluxo depois de mudar `src/`: `docker compose up -d`, esperar `healthy` e então `pytest`.

Dica opcional: se você rodou versões antigas do projeto, podem sobrar volumes do Docker sem uso. Liste com `docker volume ls -f dangling=true` e remova com `docker volume prune`. Atenção: o `prune` remove **todos** os volumes sem container, de qualquer projeto; só rode se não houver dado que você queira manter.

### Testar Health Check

```bash
# Banco
curl -i http://localhost:8001/health_check

# Transferências
curl -i http://localhost:8002/health_check
curl -i http://localhost:8002/
```

Esperado:

| Serviço | Rota | Resposta |
|---|---|---|
| Banco | `/health_check` | `204 No Content`, **sem corpo** |
| Banco | `/` | `200 OK`, corpo `{"service": "banco"}` |
| Transferências | `/health_check` | `204 No Content`, **sem corpo** |
| Transferências | `/` | `200 OK`, corpo `{"service": "transferencias"}` |

Toda resposta do Transferências e do Banco traz o header `X-Request-ID`.

---

## Tech Stack

| Camada | Tecnologia |
|--------|-----------|
| **Runtime** | Python 3.11 |
| **Framework** | FastAPI + Uvicorn |
| **ORM/SQL** | SQLAlchemy + psycopg2 |
| **Banco de dados** | PostgreSQL (duas instâncias) |
| **Conteinerização** | Docker + Docker Compose |
| **Testes** | pytest |
| **Ambiente** | Variables via `.env` (opcional) |

### Detalhes

- **FastAPI:** Framework web async, validação automática (JSON Schema).
- **SQLAlchemy:** ORM com suporte a transactions ACID.
- **PostgreSQL:** Duas instâncias separadas (uma por serviço); ledger usa partida dobrada com constraints de integridade.
- **Docker Compose:** Orquestração local; ambiente reproduzível.
- **TDD:** Testes em pytest, caixa-preta via HTTP (sem imports de `src/`).

---

## Arquitetura (Visão Geral)

```
┌─────────────────────────────────────────────────────────┐
│                    Cliente (Browser/App)                │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
   ┌────v─────────┐      ┌───────v──────────┐
   │  Banco API   │      │ Transferências   │
   │  (8001)      │      │  API (8002)      │
   └────┬─────────┘      └───────┬──────────┘
        │                        │
   ┌────v─────────┐      ┌───────v──────────┐
   │  Banco DB    │      │ Transferências   │
   │  PostgreSQL  │      │ DB (PostgreSQL)  │
   └──────────────┘      └──────────────────┘
        │                        │
        └────────────┬───────────┘
                     │
          (via HTTP + idempotência)
```

**Banco:** Dono do ledger (partida dobrada: `transaction` + `entry`), contas, clientes, autenticação.

**Transferências:** Orquestra pagamentos, chama Banco via HTTP para mover dinheiro, gerencia janela de liberação e tarifa.

---

## Estrutura de Pastas

```
desafio_qitech/
├── banco/                    # Serviço de banco e ledger
│   ├── src/
│   │   ├── app.py           # Aplicação FastAPI
│   │   ├── resources/       # Rotas HTTP
│   │   ├── controllers/     # Lógica de negócio
│   │   ├── repositories/    # Queries ao banco
│   │   ├── models/          # Entidades SQLAlchemy
│   │   ├── schemas/         # JSON Schema (validação de entrada)
│   │   ├── dtos/            # DTOs (moldagem de saída)
│   │   ├── errors/          # Códigos de erro (RNV)
│   │   └── utils/           # Utilitários
│   ├── tests/
│   │   ├── test_*.py        # Testes de integração (pytest)
│   │   └── utils/           # Harness de testes
│   ├── database/
│   │   ├── Dockerfile       # PostgreSQL customizado
│   │   └── database.sql     # Schema e enumeradores
│   └── Dockerfile           # API (multi-stage)
│
├── transferencias/           # Serviço de transferências
│   ├── src/                  # (mesma estrutura)
│   ├── tests/
│   ├── database/
│   └── Dockerfile
│
├── docker-compose.yml        # Orquestração local
└── README.md                 # Este arquivo
```

---

## Convenções de Código

- **Sem comentários.** Código fala por si: nomes claros, funções pequenas.
- **Tudo em inglês**, termos corretos de contabilidade (`ledger`, `entry`, `debit`, `credit`, `balance`).
- **Camadas, direção só para dentro:** `resource → controller → repository → model`.
  - **Resource:** HTTP (status, headers).
  - **Controller:** Regra de negócio (validações, commit).
  - **Repository:** Queries (busca, inserção).
  - **Model:** Entidade SQLAlchemy.
- **Erros:** Formato `{title, description, translation, code}` com códigos `RNV000xxx` (genérico) / `RNV001xxx` (negócio).
- **Dinheiro:** Centavos inteiros (`*_minor`, `BIGINT`). Aritmética inteira, sem `float` nem `round()`.

Para detalhes completos, leia [`CLAUDE.md`](./CLAUDE.md).

---

## Como Testar

Os testes rodam **na sua máquina** (usando o venv da raiz), contra as APIs que estão de pé no Docker. Toda vez: containers de pé (`docker compose up -d`; depois de editar `src/`, suba de novo para reconstruir a imagem, senão o teste roda contra o código antigo), venv ativo (`(.venv)` no prompt) e, a partir da **raiz**:

```bash
pytest
```

Se a API não estiver de pé, a suíte aborta com a mensagem pedindo `docker compose up -d`.

O `pytest` na raiz roda `banco` e `transferencias` em sequência, imprimindo `=== banco ===` e `=== transferencias ===`. Isso é de propósito: os dois serviços têm um pacote `tests` com o mesmo nome, então o `conftest.py` da raiz roda cada serviço em um processo separado. A saída fica assim (contagens de hoje, com a API de pé):

```
=== banco ===
2 passed

=== transferencias ===
29 passed
```

Comandos úteis (sempre da raiz, com o venv ativo):

```bash
pytest -v                # verboso
pytest -q                # resumido
pytest -k concurrent     # as flags são repassadas aos dois serviços
pytest banco/tests -v    # só o banco
pytest transferencias/tests -v    # só as transferências
pytest transferencias/tests/integration/payment/test_payment_idempotency.py -v    # um arquivo
```

Rodar `cd banco && pytest` ou `cd transferencias && pytest` não é obrigatório, mas também funciona, com o mesmo venv da raiz.

Testes:
- Caixa-preta via HTTP (não importam `src/`).
- Conversam com as APIs por HTTP, como um cliente de verdade.
- Um teste = uma regra (caminho feliz + cada código de erro RNV).

---

## Problemas comuns

- **`ModuleNotFoundError` ou `pytest: command not found`** → o venv não está ativado. Confira se o prompt mostra `(.venv)`; se não, rode `source .venv/bin/activate` na raiz (Windows: veja os comandos acima).
- **`could not reach the ... API`** (a mensagem manda rodar `docker compose up -d` primeiro) → os containers não estão de pé. Rode `docker compose up -d` e espere ficarem `healthy` (`docker compose ps`).
- **Porta ocupada (8001/8002/5433/5434)** → outra instância ou containers antigos. Rode `docker compose down` e suba de novo.
- **Criou venv dentro de `banco/` ou `transferencias/`** → apague (`rm -rf banco/.venv transferencias/.venv`) e use o `.venv` da raiz.
- **Mudou o schema do banco e nada mudou** → o `database.sql` só roda quando o container do banco é criado. Rode `docker compose down && docker compose up -d` (o banco é efêmero, volta do zero).
- **Mudei o código e o comportamento não mudou** → o container serve o código da imagem, sem `--reload`. Rode `docker compose up -d` para reconstruir; `restart` não basta.
- **Os dados sumiram depois de `restart`/`stop` no banco** → esperado: o banco é `tmpfs` e zera sempre que o container para. Veja [Containers efêmeros](#containers-efêmeros-como-atualizar).

---

## Variáveis de Ambiente

Opcionais (têm defaults):

```bash
# Banco
BANCO_DB_USER=rnv
BANCO_DB_PASSWORD=rnv
BANCO_DB_NAME=banco
BANCO_DB_PORT=5434
BANCO_API_PORT=8001

# Transferências
TRANSF_DB_USER=rnv
TRANSF_DB_PASSWORD=rnv
TRANSF_DB_NAME=transferencias
TRANSF_DB_PORT=5433
TRANSF_API_PORT=8002

# Comunicação entre serviços
INTERNAL_TOKEN=internal-token-dev
BANK_API_URL=http://banco-api:8001
```

Crie um `.env` na raiz se quiser sobrescrever.

O `docker compose` monta a `DATABASE_URL` de cada API a partir das variáveis `*_DB_*` acima, então não precisa configurar nada para rodar. Dentro do código não existe URL de banco de fallback: uma API iniciada sem `DATABASE_URL` não sobe e acusa a variável que falta. Os valores `rnv` e `internal-token-dev` são só para desenvolvimento local; em qualquer outro ambiente defina os seus no `.env`.

