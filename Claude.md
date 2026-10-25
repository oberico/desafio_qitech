# CLAUDE.md

Instituição de pagamento com conta PJ e gateway de pagamento (agnóstico à forma). **Não oferecemos crédito** — só movimentamos dinheiro de terceiros, sem assumir risco de crédito nem exigir capital próprio. Desafio do Bootcamp QI Tech. Monorepo com **dois serviços de negócio**: `banco/` e `transferencias/`; mais `external-mocks/`, container à parte que simula sistemas externos (interbancário hoje, birô depois) — sem banco, sem auth, estado em memória, chamado só pelos conectores dos serviços de negócio. Contrato em `docs/mocks-externos.md`.

Antes de codar, leia `docs/rfc-rnv-v8.0.md` (a spec; o modelo de dados completo está em `docs/modelo-de-dados.md`, e a `internal_docs/rfc-rnv-v7.2.md` fica como registro da defesa) e `internal_docs/analise-defesa-rfc.md` (o porquê de cada decisão) e `docs/catalogo-de-erros.md` (o catálogo de erros). Em conflito, a RFC v8.0 vence e você me avisa. Em caso de dúvida me pergunte e me ajude a entender melhor as regras. Não faça suposições.


**Método: TDD.** Toda construção começa pelo teste — escreve, vê falhar (red), implementa o mínimo até passar (green), refatora com a rede verde. O teste é o contrato; nenhuma fatia começa sem ele. Passo a passo em `internal_docs/roadmap-construcao-api.md`.

**Como ler o roadmap `internal_docs/roadmap-construcao-api.md`:** é o padrão de construção do base-api. Ao aplicá-lo neste projeto: (1) o prefixo de erro é `RNV`, não `QIT`; (2) a Fase 4 (fila/SQS) é histórico — NÃO construir, a arquitetura é síncrona; (3) o método é TDD test-first — o teste da fatia vem antes dos arquivos, apesar de o checklist listá-lo por último; (4) `sample_entity` e suas regras são exemplo de padrão, não o domínio.

## Feedback da banca (fase 1) — fase de correção

O `avaliacao.md` (raiz) é o parecer dos tech leads sobre o commit `161ffef`: nota 0,0, eliminado no ESC-01, 6/16 critérios. **O parecer da banca tem precedência sobre a RFC v8.0 e sobre as convenções deste arquivo.** Onde houver conflito, a banca vence; ao implementar cada ponto, a RFC, `docs/` e este CLAUDE.md são atualizados para refletir a mudança (nada de documento desatualizado). Objetivo desta fase: aprendizado e fechar o projeto como referência futura — sem pressa, um ponto por vez, com a explicação do porquê.

**Como trabalhar a correção**
- Um critério por vez, cada um em branch própria (`fix/<id-do-criterio>`) e PR próprio. Antes de codar, apresentar o plano e o impacto (rotas, schema, testes, docs) e esperar o ok.
- TDD continua valendo: o teste que reproduz a falha da banca vem primeiro (red), depois a correção (green), depois refatora.
- Mudança que quebra invariante de dinheiro, concorrência ou idempotência: explicar o risco antes.
- Divisão por agente: **Hann** (leitura do parecer, pesquisa, atualização de RFC/docs/catálogo), **Chaz** (fatias de código e testes), **Rune** (refactors amplos: rotas, `*_key`, `*_status_event`, commit), **Wren** (compose, MockServer, CI).

**Pendências, em ordem de ataque** (marcar `[x]` ao fechar, com o PR)
1. [ ] **ESC-01** — eliminatório. `POST /payouts` calcula e lança a tarifa, com a perna de receita no livro; teste confere o saldo debitado com a tarifa.
2. [ ] **COD-12** — JSON Schema em todas as rotas não-GET com corpo (9 rotas), validado antes do controller (`400 RNV000007` a `RNV000010`).
3. [ ] **COD-11** — commit só no fim do método público do controller (`_attempt`, `_finish`, `_release`).
4. [ ] **COD-04** — remover `TestClient` dos 4 testes; passam a chamar a API no ar via harness HTTP.
5. [ ] **COD-02** — teste 2xx para cada rota `/admin/*` sem cobertura.
6. [ ] **COD-13** — MockServer no compose para os 4 endpoints de connector (inclui migrar o interbancário de `external-mocks/` `.py`), um teste por endpoint.
7. [ ] **COD-10** — rotas REST no singular, sem prefixo `/internal`, `GET` no plural paginado (`limit/page/offset`).
8. [ ] **COD-05** — `*_key` unique em `api_token` e `entry`; `payment`/`payout` referenciam por `id`.
9. [ ] **COD-07** — tabelas `*_status_event`, gravando cada mudança de status.
10. [ ] **RFC-01** — RFC fiel à implementação (omissões: `GET /me`, `GET /internal/internal-accounts`, status `created`, tabelas de transição) e erros declarados nunca levantados (observação do COD-03).

Os itens 7–9 contradizem decisões atuais deste arquivo (UUID opaco entre serviços, `allowed_transition`, plural nas rotas). Antes de cada um, alinhar comigo o desenho de migração, porque mexem em muitos arquivos e nos testes.

## Tese da arquitetura

- O **dinheiro tem um dono só**: o livro-razão de partida dobrada (`transaction` + `entry`) mora inteiro no **Banco**. O **Transferências** orquestra o produto de pagamento e chama o Banco para mover dinheiro.
- Comunicação entre serviços: **HTTP síncrono + idempotência**. Sem saga, sem message broker. A atomicidade fica no banco de dados do Banco.
- A direção das chamadas é Transferências → Banco, com **uma única exceção deliberada**: no `POST /accounts/{key}/close`, o Banco chama `GET /internal/accounts/{key}/in-flight` no Transferências (vendas `held` e saques `pending`) por `banco/src/connectors/transferencias_connector.py`. É fail-closed: sem resposta, `503 RNV001036` e a conta continua `active`; com algo em trânsito ou saldo, `422 RNV001035`. Não duplicar o estado de vendas e saques no Banco.
- A **identidade** segue a mesma regra: o token nasce no Banco; o Transferências valida chamando `GET /auth/me` no Banco. Nunca duplicar a tabela de cliente.
- **Sem cross-service no nível de dados.** Dois bancos separados (um por serviço); nenhuma FK atravessa serviços. Entre serviços só trafega a chave pública (UUID): o `payment` referencia a `transaction`/`account` do Banco por UUID, como valor opaco, nunca por FK nem join.

## Convenções de código (valem para os dois serviços)

- **Sem comentários.** O código fala por si: nomes claros, funções pequenas.
- **Tudo em inglês**, com os termos corretos de contabilidade e banco (`normal_balance`, `ledger`, `entry`, `asset`/`liability`/`revenue`).
- **Camadas, direção só para dentro:** `resource → controller → repository → model`. Repository só faz query (devolve dado ou vazio); controller faz regra de negócio e dá o commit; resource fala HTTP e decide o status; nenhum `raise` no resource. **Não existe camada `service`** — não crie uma.
- **Erros** no formato `{title, description, translation, code}`, código estável `RNV000xxx` (genérico) / `RNV001xxx` (negócio). Sem código duplicado. Leia `docs/catalogo-de-erros.md` para ver os códigos de erro que já existem e use-os corretamente. Em caso de dúvida ou sugestão de novos códigos, me pergunte antes de criar.
- **JSON Schema na porta** valida o formato do corpo e da query antes de qualquer consulta, com um código por tipo de erro (`400`): `RNV000007` campo obrigatório ausente, `RNV000008` campo ou parâmetro não permitido, `RNV000009` tipo, formato ou enumerador inválido, `RNV000010` valor fora do limite, `RNV000011` cursor inválido, `RNV000012` header `Idempotency-Key` ausente ou fora do tamanho. `RNV000001` ficou só para corpo que não é objeto JSON. Pydantic não é usado para contrato de entrada.
- **Enumeradores são tabelas de lookup** (`enumerator` UK + FK), nunca texto solto nem `ENUM` nativo. Valores em **minúsculo** (`pending`, `gateway`, `brl`, `d`/`c`); códigos de erro (`RNV000001`…) em maiúsculo.
- **Datas com fuso:** toda coluna de data é `TIMESTAMPTZ` (no model, `DateTime(timezone=True)`).
- **Chaves:** `id` interno `SERIAL` (nunca exposto, nunca cruza serviço); chave pública `CHAR(36)` UUID v4 (é o que sai na resposta e o único que trafega entre serviços).
- **Dinheiro em centavos inteiros** (`*_minor`, `BIGINT`). Aritmética inteira, **nunca float, nunca `round()`** (arredondamento bancário é proibido em dinheiro). Tarifa arredonda **para cima**: `fee = (amount_minor * fee_bps + 9999) // 10000`, `net = amount_minor - fee`; o centavo residual fica com o cliente. Invariante: `fee + net == amount_minor`, exato.
- **Tarifa de payout (por cima):** mesma conta, `fee_minor = (amount_minor * fee_bps + 9999) // 10000`, mas o destino recebe `amount_minor` inteiro e o cliente é debitado `amount_minor + fee_minor`. `POST /payouts` lança D cliente `amount+fee` · C `in_transit` `amount` · C `revenue` `fee`; a reversal estorna valor e tarifa (D `revenue` `fee` · D `in_transit` `amount` · C cliente `amount+fee`). Tarifa única como dado (`payout_fee`, versionada e append-only, `PUT /internal/payout-fee`), versão 1 semeada com 50 bps, `payout.fee_id` (`NOT NULL`, FK para `payout_fee.id`, nunca exposto) mais snapshot `fee_bps`/`fee_minor` no `payout`; não entra no `payload_hash`.
- **Partida dobrada:** `entry` com `debit_minor`/`credit_minor` (constraint: exatamente um > 0, nenhum negativo); soma de débito = soma de crédito por transação.
- **Saldo derivado**, nunca armazenado: `SUM(credit_minor) - SUM(debit_minor)` nas `entry` da conta. **Sem `balance_after`** — a `entry` é append-only e um snapshot cravado numa linha imutável é lost update garantido. Contas internas são reconciliadas em lote (não ficam no caminho da request). Se o volume exigir, a evolução é um saldo materializado em linha **mutável e reconstruível**, atualizado na mesma transação com incremento atômico — nunca `balance_after`.
- **Append-only:** nada é apagado; correção é lançamento novo (estorno/reembolso). "Encerrar" é PUT de status. Tentativas de payout também são append-only (`payout_attempt`, uma linha por tentativa); o número de tentativas é derivado (`COUNT`), não um contador mutável.
- **Idempotência — na própria entidade, sem tabela separada.** Cada operação idempotente carrega `idempotency_key` + `payload_hash` (SHA-256 do JSON canônico dos campos que definem o pedido) na SUA tabela: `transaction` no Banco, `payment` e `payout` no Transferências. `UNIQUE` nomeado, escopado por empresa (company_key + operação quando precisar distinguir).
- O insert com a chave é a **primeira escrita** da operação. Se o `UNIQUE` estourar: `rollback`, busca a linha pela chave e compara o `payload_hash` — igual, devolve o estado **atual** da entidade (via DTO) com `200`; diferente, `422 RNV001024`.
- A resposta do retry é **reconstruída do DTO** da entidade (estado atual), não um snapshot gravado. Consequência consciente: um retry tardio reflete o agora (um payout já liquidado volta `settled`/`200`, não o `pending`/`201` original). Erros não são cacheados: tentativa que deu rollback libera a chave para nova tentativa.
- Toda chave de lançamento no Banco é determinística, para o retry reencontrar o lançamento. Derivadas da chave do cliente: `receipt:<company_key>:<chave>` e `payout:<company_key>:<chave>`. Derivadas da entidade, disparadas por job ou estorno: `settlement:<payment_key>`, `refund:<payment_key>`, `settlement:<payout_key>`, `reversal:<payout_key>` e `orphan-refund:<transaction_key>` (reconciliação de recebimento sem venda).
- A chave é do cliente; o banco **não adivinha intenção**. A chave nunca expira. **Não há tabela `idempotency` genérica nem `response_body` gravado.**
- **CPF/CNPJ mascarados** (`CHAR(14)`/`CHAR(18)`, `pattern` com pontuação).
- **Máquina de estados:** as transições permitidas moram em tabela (`allowed_transition` no Banco; `payment_transition`/`payout_transition` no Transferências) e o controller consulta antes de trocar o status. A conta é a exceção: as transições dela (na abertura, `active` ou `rejected` pelo birô; depois `active → blocked | closed` e `blocked → active`) são conferidas no próprio `AccountController`, pelo status atual (`409 RNV001009`/`RNV001010`). **O ledger só responde "o dinheiro se moveu?": `pending`/`settled`** — sem `failed` (ou faz settlement, ou faz reversal; o estorno não muda o status do original, quem marca é a reversal via `reverses_transaction_id` único). `failed` existe só em `payout_status`. `payment`: `held`/`settled`/`refunded`.
- **Concorrência:** no **débito**, `SELECT ... FOR UPDATE` na **linha da `account`** (não na `entry`, que é append-only e não tem linha pra travar), soma o saldo **depois** de travar, confere, insere, commit — em **READ COMMITTED** (não mudar para REPEATABLE READ, quebra a conferência). Duas contas na mesma operação: travar na ordem do **id menor**. Crédito **não trava**; conta interna **nunca** trava. Na corrida saída × estorno, trava a **linha do `payment`** e relê o status; `settles_transaction_id` único garante uma saída por venda.

## Contrato de rotas

O contrato canônico de rotas vive em `docs/rotas.md` — o que cada endpoint recebe, devolve, quem acessa e quais erros RNV pode retornar. **Antes de implementar qualquer rota, consulte esse documento.** Em conflito com o código, `rotas.md` vence e você me avisa. Os códigos de erro em si estão em `docs/catalogo-de-erros.md`.

## Autenticação

- **público** (bypass): `/`, `/health_check`, `POST /clients`.
- **cliente**: header `Authorization: Bearer <token>` → `401 RNV000003` se faltar/for inválido.
- **admin**: rotas `/admin/*` (nos dois serviços) com `Authorization: Bearer <ADMIN_TOKEN>`; o token vem da env `ADMIN_TOKEN` (não existe tabela de admin). Ausente/inválido → `401 RNV000003`; o `INTERNAL-TOKEN` não vale (também `401`); token de cliente válido → `403 RNV001027`.
- **serviço**: rotas `/internal/*` e as chamadas entre serviços com `INTERNAL-TOKEN` → `403 RNV000002`.
- Token hasheado no banco (SHA-256), com rotação (`revoked_at`). Contra IDOR: `404`, não 403.
- O token **autentica** (middleware); cada rota **autoriza** (controller): empresa sem conta aberta → `403 RNV001030` (não se aplica ao `POST /payouts`, que identifica a conta pela `account_key`); conta fora de `active` → `403 RNV001031` na escrita (leitura de saldo, extrato e consultas passa com a conta `blocked`/`closed`). O birô valida a empresa uma vez, na abertura da conta, e **não tem código próprio**: a reprovação deixa a conta `rejected`, um estado "não active" que cai em `RNV001031`. Empresa reprovada não reabre conta.

## Como construir uma entidade (ordem por fatia)

`database.sql` → `models/` → `repositories/` → `controllers/` (+ `errors/`) → `schemas/` (JSON) → `dtos/` → `resources/` + registro no `app.py` → testes de integração. Registrar cada arquivo no `__init__.py` na ordem de dependência (evita circular import).

## Docker e banco

- Cada serviço tem seu `database/database.sql`, que roda **uma vez** na criação do volume. Mexeu no schema: `docker compose down -v && docker compose up`. Não existe migration; o `.sql` é a fonte de verdade.
- **Seed: enumeradores e tarifas.** Além dos enumeradores, as tarifas são dado semeado no `transferencias/database/database.sql`: `payment_method` (versão 1 por meio) e a versão 1 de `payout_fee` (`fee_bps = 50`), de modo que sempre há versão vigente. Nenhum outro seed. As contas internas continuam por get-or-create. São três contas internas, criadas no controller/testes por get-or-create pelo `code`: `reserves` (ativo — o dinheiro que o banco de fato tem), `in_transit` (passivo — recebido e ainda na janela, ou pedido e ainda não saído) e `revenue` (receita — as taxas).
- `psycopg2-binary` fica pinado (quebra em Mac ARM sem o pin).

## Testes — TDD é o método, não um passo final

- **O teste vem primeiro.** Por fatia: escreve o teste de integração, roda e vê **falhar** (red); implementa o mínimo até **passar** (green); **refatora** com a rede verde.
- Caixa-preta, por HTTP, como cliente: usa o harness de `tests/utils/` (`RequestGenerator`, `PayloadGenerator`, `RandomGenerator`); **nunca importa de `src/`**.
- Um teste = uma regra. Cobrir o caminho feliz e **cada** código de erro RNV (400/401/403/404/409/422). A lista de erros da RFC já é a lista de testes a escrever.
- Testes obrigatórios de concorrência e dinheiro: dois débitos simultâneos (um passa, um `422`, saldo nunca negativo); N créditos simultâneos (todos entram, saldo = soma); 10x a mesma Idempotency-Key (uma operação); taxa snapshotada (muda a taxa entre chegada e liberação → cobra a antiga); estorno cheio na janela, recusado depois de `settled`; 3 timeouts de payout → `failed` + reversal devolve o dinheiro.
- A API precisa estar de pé (`docker compose up`); o teste fala por HTTP e checa `status` + `response["code"]`.

## Fronteira dos serviços

- **Banco** é dono de: `client`, `company`, `account`, `api_token`, ledger (`transaction`/`entry`), auth. Expõe `POST /ledger/transactions` (lançamento idempotente), `GET /auth/me`, `GET /internal/ledger/receipts` e `GET /internal/internal-accounts` (só com `INTERNAL-TOKEN`). No `close`, chama o Transferências (`GET /internal/accounts/{key}/in-flight`), a única chamada do Banco para fora.
- **Transferências** é dono de: `payment`, `payout` (com `destination` jsonb dado na requisição, imutável), `payout_attempt`, o ciclo (janela `release_at`, tarifa por `payment_method`, estados). Chama o Banco por `connectors/bank_connector.py` e o interbancário (mock em `external-mocks/`, `POST /interbank/transfers`) por `connectors/interbank_connector.py`, com `INTERBANK_API_URL` e `INTERBANK_TIMEOUT_SECONDS`. O birô é hoje o `MockBureauConnector` dentro do Banco; migra para o `external-mocks/` numa fatia própria.
- Taxa e janela são **dado** (`payment_method`: `fee_bps` + janela por meio), snapshotados no `payment` na chegada; o settle usa o snapshot. A tarifa de saída também é dado (`payout_fee`), snapshotada no `payout` no pedido. O cálculo da tarifa e a escolha das contas é do **Transferências**; o Banco só valida que os lançamentos fecham e dedupe.
