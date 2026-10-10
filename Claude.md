# CLAUDE.md

Instituição de pagamento com conta PJ e gateway de pagamento (agnóstico à forma). **Não oferecemos crédito** — só movimentamos dinheiro de terceiros, sem assumir risco de crédito nem exigir capital próprio. Desafio do Bootcamp QI Tech. Monorepo com **dois serviços**: `banco/` e `transferencias/`.

Antes de codar, leia `internal_docs/rfc-rnv-v7.2.md` (a spec) e `internal_docs/analise-defesa-rfc.md` (o porquê de cada decisão) e `internal_docs/catalogo-de-erros.md` (o catálogo de erros). Em conflito, a RFC v7.2 vence e você me avisa. Em caso de dúvida me pergunte e me ajude a entender melhor as regras. Não faça suposições.

**Método: TDD.** Toda construção começa pelo teste — escreve, vê falhar (red), implementa o mínimo até passar (green), refatora com a rede verde. O teste é o contrato; nenhuma fatia começa sem ele. Passo a passo em `internal_docs/roadmap-construcao-api.md`.

**Como ler o roadmap `internal_docs/roadmap-construcao-api.md`:** é o padrão de construção do base-api. Ao aplicá-lo neste projeto: (1) o prefixo de erro é `RNV`, não `QIT`; (2) a Fase 4 (fila/SQS) é histórico — NÃO construir, a arquitetura é síncrona; (3) o método é TDD test-first — o teste da fatia vem antes dos arquivos, apesar de o checklist listá-lo por último; (4) `sample_entity` e suas regras são exemplo de padrão, não o domínio.

## Tese da arquitetura

- O **dinheiro tem um dono só**: o livro-razão de partida dobrada (`transaction` + `entry`) mora inteiro no **Banco**. O **Transferências** orquestra o produto de pagamento e chama o Banco para mover dinheiro.
- Comunicação entre serviços: **HTTP síncrono + idempotência**. Sem saga, sem message broker. A atomicidade fica no banco de dados do Banco.
- A **identidade** segue a mesma regra: o token nasce no Banco; o Transferências valida chamando `GET /auth/me` no Banco. Nunca duplicar a tabela de cliente.
- **Sem cross-service no nível de dados.** Dois bancos separados (um por serviço); nenhuma FK atravessa serviços. Entre serviços só trafega a chave pública (UUID): o `payment` referencia a `transaction`/`account` do Banco por UUID, como valor opaco, nunca por FK nem join.

## Convenções de código (valem para os dois serviços)

- **Sem comentários.** O código fala por si: nomes claros, funções pequenas.
- **Tudo em inglês**, com os termos corretos de contabilidade e banco (`normal_balance`, `ledger`, `entry`, `asset`/`liability`/`revenue`).
- **Camadas, direção só para dentro:** `resource → controller → repository → model`. Repository só faz query (devolve dado ou vazio); controller faz regra de negócio e dá o commit; resource fala HTTP e decide o status; nenhum `raise` no resource. **Não existe camada `service`** — não crie uma.
- **Erros** no formato `{title, description, translation, code}`, código estável `RNV000xxx` (genérico) / `RNV001xxx` (negócio). Sem código duplicado. Leia `internal_docs/catalogo-de-erros.md` para ver os códigos de erro que já existem e use-os corretamente. Em caso de dúvida ou sugestão de novos códigos, me pergunte antes de criar.
- **JSON Schema na porta** valida o formato do corpo antes de qualquer consulta (`400 RNV000001`). Pydantic não é usado para contrato de entrada.
- **Enumeradores são tabelas de lookup** (`enumerator` UK + FK), nunca texto solto nem `ENUM` nativo. Valores em **minúsculo** (`pending`, `gateway`, `brl`, `d`/`c`); códigos de erro (`RNV000001`…) em maiúsculo.
- **Datas com fuso:** toda coluna de data é `TIMESTAMPTZ` (no model, `DateTime(timezone=True)`).
- **Chaves:** `id` interno `SERIAL` (nunca exposto, nunca cruza serviço); chave pública `CHAR(36)` UUID v4 (é o que sai na resposta e o único que trafega entre serviços).
- **Dinheiro em centavos inteiros** (`*_minor`, `BIGINT`). Aritmética inteira, **nunca float, nunca `round()`** (arredondamento bancário é proibido em dinheiro). Tarifa arredonda **para cima**: `fee = (amount_minor * fee_bps + 9999) // 10000`, `net = amount_minor - fee`; o centavo residual fica com o cliente. Invariante: `fee + net == amount_minor`, exato.
- **Partida dobrada:** `entry` com `debit_minor`/`credit_minor` (constraint: exatamente um > 0, nenhum negativo); soma de débito = soma de crédito por transação.
- **Saldo derivado**, nunca armazenado: `SUM(credit_minor) - SUM(debit_minor)` nas `entry` da conta. **Sem `balance_after`** — a `entry` é append-only e um snapshot cravado numa linha imutável é lost update garantido. Contas internas são reconciliadas em lote (não ficam no caminho da request). Se o volume exigir, a evolução é um saldo materializado em linha **mutável e reconstruível**, atualizado na mesma transação com incremento atômico — nunca `balance_after`.
- **Append-only:** nada é apagado; correção é lançamento novo (estorno/reembolso). "Encerrar" é PUT de status. Tentativas de payout também são append-only (`payout_attempt`, uma linha por tentativa); o número de tentativas é derivado (`COUNT`), não um contador mutável.
- **Idempotência — na própria entidade, sem tabela separada.** Cada operação idempotente carrega `idempotency_key` + `payload_hash` (SHA-256 do JSON canônico dos campos que definem o pedido) na SUA tabela: `transaction` no Banco, `payment` e `payout` no Transferências. `UNIQUE` nomeado, escopado por empresa (company_key + operação quando precisar distinguir).
- O insert com a chave é a **primeira escrita** da operação. Se o `UNIQUE` estourar: `rollback`, busca a linha pela chave e compara o `payload_hash` — igual, devolve o estado **atual** da entidade (via DTO) com `200`; diferente, `422 RNV001024`.
- A resposta do retry é **reconstruída do DTO** da entidade (estado atual), não um snapshot gravado. Consequência consciente: um retry tardio reflete o agora (um payout já liquidado volta `settled`/`200`, não o `pending`/`201` original). Erros não são cacheados: tentativa que deu rollback libera a chave para nova tentativa.
- Lançamentos criados por job usam chave determinística (`settlement:<payment_key>`, `payout:<payout_key>`), para o retry reencontrar o lançamento no Banco.
- A chave é do cliente; o banco **não adivinha intenção**. A chave nunca expira. **Não há tabela `idempotency` genérica nem `response_body` gravado.**
- **CPF/CNPJ mascarados** (`CHAR(14)`/`CHAR(18)`, `pattern` com pontuação).
- **Máquina de estados:** as transições permitidas moram em tabela (`allowed_transition` no Banco; `payment_transition`/`payout_transition` no Transferências) e o controller consulta antes de trocar o status. A conta usa o util `state_machine.py`. **O ledger só responde "o dinheiro se moveu?": `pending`/`settled`** — sem `failed` (ou faz settlement, ou faz reversal; o estorno não muda o status do original, quem marca é a reversal via `reverses_transaction_id` único). `failed` existe só em `payout_status`. `payment`: `held`/`settled`/`refunded`.
- **Concorrência:** no **débito**, `SELECT ... FOR UPDATE` na **linha da `account`** (não na `entry`, que é append-only e não tem linha pra travar), soma o saldo **depois** de travar, confere, insere, commit — em **READ COMMITTED** (não mudar para REPEATABLE READ, quebra a conferência). Duas contas na mesma operação: travar na ordem do **id menor**. Crédito **não trava**; conta interna **nunca** trava. Na corrida saída × estorno, trava a **linha do `payment`** e relê o status; `settles_transaction_id` único garante uma saída por venda.

## Contrato de rotas

O contrato canônico de rotas vive em `internal_docs/rotas.md` — o que cada endpoint recebe, devolve, quem acessa e quais erros RNV pode retornar. **Antes de implementar qualquer rota, consulte esse documento.** Em conflito com o código, `rotas.md` vence e você me avisa. Os códigos de erro em si estão em `internal_docs/catalogo-de-erros.md`.

## Autenticação

- **público** (bypass): `/`, `/health_check`, `POST /clients`.
- **cliente**: header `Authorization` com o token → `401 RNV000003` se faltar/for inválido.
- **admin**: rotas `/admin/*` com token de admin.
- **serviço**: rotas `/internal/*` e as chamadas entre serviços com `INTERNAL-TOKEN` → `403 RNV000002`.
- Token hasheado no banco (SHA-256), com rotação (`revoked_at`). Contra IDOR: `404`, não 403.
- O token **autentica** (middleware); cada rota **autoriza** (controller): falta company validada pelo birô → `403` (código próprio); falta conta `active` → `403` (código próprio).

## Como construir uma entidade (ordem por fatia)

`database.sql` → `models/` → `repositories/` → `controllers/` (+ `errors/`) → `schemas/` (JSON) → `dtos/` → `resources/` + registro no `app.py` → testes de integração. Registrar cada arquivo no `__init__.py` na ordem de dependência (evita circular import).

## Docker e banco

- Cada serviço tem seu `database/database.sql`, que roda **uma vez** na criação do volume. Mexeu no schema: `docker compose down -v && docker compose up`. Não existe migration; o `.sql` é a fonte de verdade.
- **Sem seed além dos enumeradores.** São três contas internas, criadas no controller/testes por get-or-create pelo `code`: `reserves` (ativo — o dinheiro que o banco de fato tem), `in_transit` (passivo — recebido e ainda na janela, ou pedido e ainda não saído) e `revenue` (receita — as taxas).
- `psycopg2-binary` fica pinado (quebra em Mac ARM sem o pin).

## Testes — TDD é o método, não um passo final

- **O teste vem primeiro.** Por fatia: escreve o teste de integração, roda e vê **falhar** (red); implementa o mínimo até **passar** (green); **refatora** com a rede verde.
- Caixa-preta, por HTTP, como cliente: usa o harness de `tests/utils/` (`RequestGenerator`, `PayloadGenerator`, `RandomGenerator`); **nunca importa de `src/`**.
- Um teste = uma regra. Cobrir o caminho feliz e **cada** código de erro RNV (400/401/403/404/409/422). A lista de erros da RFC já é a lista de testes a escrever.
- Testes obrigatórios de concorrência e dinheiro: dois débitos simultâneos (um passa, um `422`, saldo nunca negativo); N créditos simultâneos (todos entram, saldo = soma); 10x a mesma Idempotency-Key (uma operação); taxa snapshotada (muda a taxa entre chegada e liberação → cobra a antiga); estorno cheio na janela, recusado depois de `settled`; 3 timeouts de payout → `failed` + reversal devolve o dinheiro.
- A API precisa estar de pé (`docker compose up`); o teste fala por HTTP e checa `status` + `response["code"]`.

## Fronteira dos serviços

- **Banco** é dono de: `client`, `company`, `account`, `api_token`, ledger (`transaction`/`entry`), auth. Expõe `POST /ledger/transactions` (lançamento idempotente) e `GET /auth/me` (só com `INTERNAL-TOKEN`).
- **Transferências** é dono de: `payment`, `payout` (com `destination` jsonb dado na requisição, imutável), `payout_attempt`, o ciclo (janela `release_at`, tarifa por `payment_method`, estados). Chama o Banco por `connectors/bank_connector.py` e o mock por `connectors/interbank_connector.py`.
- Taxa e janela são **dado** (`payment_method`: `fee_bps` + janela por meio), snapshotados no `payment` na chegada; o settle usa o snapshot. O cálculo da tarifa e a escolha das contas é do **Transferências**; o Banco só valida que os lançamentos fecham e dedupe.
