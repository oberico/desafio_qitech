# CLAUDE.md

Instituição de pagamento com conta PJ e gateway de pagamento (agnóstico à forma). **Não oferecemos crédito** — só movimentamos dinheiro de terceiros, sem assumir risco de crédito nem exigir capital próprio. Desafio do Bootcamp QI Tech. Monorepo com **dois serviços**: `banco/` e `transferencias/`.

**Método: TDD.** Toda construção começa pelo teste — escreve, vê falhar (red), implementa o mínimo até passar (green), refatora com a rede verde. O teste é o contrato; nenhuma fatia começa sem ele. Passo a passo em `manual-desenvolvimento.md`.

## Tese da arquitetura

- O **dinheiro tem um dono só**: o livro-razão de partida dobrada (`transaction` + `entry`) mora inteiro no **Banco**. O **Transferências** orquestra o produto de pagamento e chama o Banco para mover dinheiro.
- Comunicação entre serviços: **HTTP síncrono + idempotência**. Sem saga, sem message broker. A atomicidade fica no banco de dados do Banco.
- A **identidade** segue a mesma regra: o token nasce no Banco; o Transferências valida chamando `GET /auth/me` no Banco. Nunca duplicar a tabela de cliente.
- Dois bancos de dados separados (um por serviço). O `payment` referencia a `transaction` do Banco pela chave pública (UUID), nunca por FK.

## Convenções de código (valem para os dois serviços)

- **Sem comentários.** O código fala por si: nomes claros, funções pequenas.
- **Tudo em inglês**, com os termos corretos de contabilidade e banco (`normal_balance`, `balance_after`, `ledger`, `entry`, `asset`/`liability`/`revenue`).
- **Camadas, direção só para dentro:** `resource → controller → repository → model`. Repository só faz query; controller faz regra de negócio; resource fala HTTP e decide o status; nenhum `raise` no resource.
- **Erros** no formato `{title, description, translation, code}`, código estável `RNV000xxx` (genérico) / `RNV001xxx` (negócio). Sem código duplicado.
- **JSON Schema na porta** valida o formato do corpo antes de qualquer consulta (`400 RNV000001`). Pydantic não é usado para contrato de entrada.
- **Enumeradores são tabelas de lookup** (`enumerator` UK + FK), nunca texto solto nem `ENUM` nativo.
- **Chaves:** `id` interno `SERIAL`; chave pública `CHAR(36)` UUID v4 (é o que sai na resposta, nunca o `id`).
- **Dinheiro em centavos inteiros** (`*_minor`, `BIGINT`); tarifa com arredondamento bancário (round half even).
- **Partida dobrada:** `entry` com `debit_minor`/`credit_minor` (constraint: exatamente um > 0); soma de débito = soma de crédito por transação.
- **Saldo:** derivado das `entry` + `balance_after` snapshot só em conta de cliente. Contas internas sem snapshot (reconciliadas em lote).
- **Append-only:** nada é apagado; correção é lançamento novo (estorno/reembolso). "Encerrar" é PUT de status.
- **CPF/CNPJ mascarados** (`CHAR(14)`/`CHAR(18)`, `pattern` com pontuação).
- **Máquina de estados** validada contra a tabela `allowed_transition` (transação) e o util `state_machine.py` (conta).
- **Concorrência:** `SELECT ... FOR UPDATE` na conta de cliente na ordem do id menor (para `balance_after`); na corrida de saída, trava a **linha da transação** e relê o status; `settles_transaction_id` único garante uma saída por venda.

## Autenticação

- **público** (bypass): `/`, `/health_check`, `POST /clients`.
- **cliente**: header `Authorization` com o token → `401 RNV000003` se faltar/for inválido.
- **admin**: rotas `/admin/*` com token de admin.
- **serviço**: rotas `/internal/*` e as chamadas entre serviços com `INTERNAL-TOKEN` → `403 RNV000002`.
- Token hasheado no banco (SHA-256), com rotação (`revoked_at`). Contra IDOR: `404`, não 403.

## Como construir uma entidade (ordem por fatia)

`database.sql` → `models/` → `repositories/` → `controllers/` (+ `errors/`) → `schemas/` (JSON) → `dtos/` → `resources/` + registro no `app.py` → testes de integração. Registrar cada arquivo no `__init__.py` na ordem de dependência (evita circular import).

## Docker e banco

- Cada serviço tem seu `database/database.sql`, que roda **uma vez** na criação do volume. Mexeu no schema: `docker compose down -v && docker compose up`.
- `psycopg2-binary` fica pinado (quebra em Mac ARM sem o pin).

## Testes — TDD é o método, não um passo final

- **O teste vem primeiro.** Por fatia: escreve o teste de integração, roda e vê **falhar** (red); implementa o mínimo até **passar** (green); **refatora** com a rede verde.
- Caixa-preta, por HTTP, como cliente: usa o harness de `tests/utils/` (`RequestGenerator`, `PayloadGenerator`, `RandomGenerator`); **nunca importa de `src/`**.
- Um teste = uma regra. Cobrir o caminho feliz e **cada** código de erro RNV (400/401/403/404/409/422). A lista de erros da RFC já é a lista de testes a escrever.
- A API precisa estar de pé (`docker compose up`); o teste fala por HTTP e checa `status` + `response["code"]`.

## Fronteira dos serviços

- **Banco** é dono de: `client`, `company`, `account`, `api_token`, ledger (`transaction`/`entry`), auth. Expõe `POST /ledger/transactions` (lançamento idempotente) e `GET /auth/me` (só com `INTERNAL-TOKEN`).
- **Transferências** é dono de: `payment`, `payout`, `external_bank_account`, o ciclo (janela `release_at`, tarifa, estados). Chama o Banco por `connectors/bank_connector.py` e o mock por `connectors/interbank_connector.py`.
- O cálculo da tarifa e a escolha das contas é do **Transferências**; o Banco só valida que os lançamentos fecham e dedupe.
