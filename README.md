# RNV — Instituição de Pagamento com Conta PJ

Instituição de pagamento que movimenta dinheiro de terceiros via gateway agnóstico. Não oferecemos crédito — apenas gerenciamos contas e transferências de forma segura e auditável.

**Desafio do Bootcamp QI Tech** · Monorepo com dois serviços independentes: `banco/` (ledger e autenticação) e `transferencias/` (orquestração de pagamentos).

---

## Quickstart — Rodar Localmente

### Pré-requisitos

- Docker & Docker Compose
- Python 3.11 (opcional, só se rodar sem containers)

### Levantar os serviços

```bash
docker compose up
```

Isso levanta:
- **banco-db** (PostgreSQL na porta 5434)
- **banco-api** (FastAPI na porta 8001)
- **transferencias-db** (PostgreSQL na porta 5433)
- **transferencias-api** (FastAPI na porta 8002)

Espere até ver `banco-api` e `transferencias-api` com status `healthy` (healthcheck passa).

### Testar Health Check

```bash
# Banco
curl http://localhost:8001/health_check

# Transferências
curl http://localhost:8002/health_check
```

Esperado:
```json
{"status": "ok"}
```

Ambas as rotas devem retornar `200 OK`.

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

Os testes rodam **na sua máquina**, contra as APIs que estão de pé no Docker. São dois passos: um de uma vez só, outro toda vez.

**Uma vez só — instalar as dependências de teste:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

No Windows, a segunda linha é `.venv\Scripts\activate`.

**Toda vez — com os containers de pé, em outro terminal:**

```bash
pytest
```

As APIs precisam estar respondendo antes. Se você acabou de dar `docker compose up`, espere os dois serviços ficarem `healthy`.

O resultado sai assim (16 verdes, 8 vermelhos esperados — payment ainda não existe):

```
banco/tests/integration/test_health_check.py::test_health_check PASSED
transferencias/tests/integration/test_health_check.py::test_health_check PASSED
transferencias/tests/integration/payment/test_payment_create.py::test_create_payment FAILED
============================== 16 passed, 8 failed in 2.1s ==============================
```

Para rodar só um arquivo:

```bash
pytest banco/tests/ -v
pytest transferencias/tests/ -v
```

Testes:
- Caixa-preta via HTTP (não importam `src/`).
- Conversam com as APIs por HTTP, como um cliente de verdade.
- Um teste = uma regra (caminho feliz + cada código de erro RNV).

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

