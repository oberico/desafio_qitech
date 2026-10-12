# Rotas — contrato da API (v7)

> **Contrato canônico de rotas.** Esta é a fonte da verdade do que cada endpoint recebe e
> devolve. Antes de implementar qualquer rota, confira aqui. Em conflito com o código, este
> documento vence e você me avisa. Alinhado com a RFC v7.2 e o catálogo de erros (`catalogo-de-erros.md`).
>
> Acessos: **público** (bypass) · **cliente** (`Authorization`) · **admin** (`/admin/*`) ·
> **serviço** (`INTERNAL-TOKEN`, rotas `/internal/*` e chamadas entre serviços).
>
> Escritas exigem header `Idempotency-Key` (ausente → `400 RNV000001`).

---

## Banco

Dono de: `client`, `company`, `account`, `api_token`, ledger (`transaction`/`entry`), auth.

### Básico (infra / health)

| Prioridade | Método | Rota | Acesso |
|---|---|---|---|
| 0 | GET | `/` | público |
| 0 | GET | `/health_check` | público |

### Cadastro e identidade

| Prioridade | Método | Rota | Acesso | Justificativa |
|---|---|---|---|---|
| 1 | POST | `/clients` | público | Cria cliente (pessoa). Nasce aqui o token. |
| 1 | POST | `/companies` | cliente | Cria empresa (PJ) sob o cliente do token. |
| 1 | GET | `/auth/me` | serviço | Identidade para o Transferências (só `INTERNAL-TOKEN`). |
| 2 | GET | `/me` | cliente | Dados do próprio cliente. |
| 2 | GET | `/companies/{company_key}` | cliente | Empresa do dono; IDOR → `404 RNV001018`. |

### Conta

| Prioridade | Método | Rota | Acesso | Justificativa |
|---|---|---|---|---|
| 1 | POST | `/companies/{company_key}/accounts` | cliente | Abre conta da empresa; valida birô; `409 RNV001022` se já tem conta. |
| 1 | GET | `/accounts/{account_key}/balance` | cliente | Saldo derivado. **Leitura passa com conta blocked/closed.** |
| 1 | GET | `/accounts/{account_key}/statement` | cliente | Extrato (entries). **Leitura passa com conta blocked/closed.** |
| 2 | GET | `/accounts/{account_key}` | cliente | Dados da conta; IDOR → `404 RNV001021`. |
| 2 | POST | `/accounts/{account_key}/close` | cliente | Encerra; `409 RNV001009` se a conta não está `active`; `422 RNV001035` se tem saldo ou valores em trânsito (payment `held`/payout `pending` no Transferências); `503 RNV000006` se o Transferências não responde (fail-closed). Ordem: lock da conta, status, saldo, consulta in-flight, muda status, commit. |

### Ledger

| Prioridade | Método | Rota | Acesso | Justificativa |
|---|---|---|---|---|
| 1 | POST | `/ledger/transactions` | serviço | Lançamento idempotente de partida dobrada. Valida fechamento e dedupe. |

**Limites do `POST /ledger/transactions`** (JSON Schema na porta, `400 RNV000001`):

- `debit_minor` e `credit_minor`: inteiros de `1` a `9223372036854775807` (teto do `BIGINT`). Acima do teto → `400 RNV000001`; antes desse limite o estouro virava `500`.
- `entries`: de `2` a `20` itens (uma transação real tem no máximo 4). Fora da faixa → `400 RNV000001`.

### Internal (bloqueio por serviço/admin)

| Prioridade | Método | Rota | Acesso | Justificativa |
|---|---|---|---|---|
| 1 | GET | `/internal/internal-accounts` | serviço | Lista as contas internas (`reserves`, `in_transit`, `revenue`) com `account_key`, `code`, `class`, `normal_balance` e `status`. Serve para o ledger e os testes referenciarem a conta pelo `account_key` real, sem acessar o banco. |
| 3 | POST | `/internal/accounts/{account_key}/block` | serviço | Bloqueia conta; `409 RNV001009` se não active. |
| 3 | POST | `/internal/accounts/{account_key}/unblock` | serviço | Desbloqueia; `409 RNV001010` se não blocked. |

### Admin

| Prioridade | Método | Rota | Acesso |
|---|---|---|---|
| 3 | GET | `/admin/clients` | admin |
| 3 | GET | `/admin/companies` | admin |
| 3 | GET | `/admin/accounts` | admin |
| 3 | GET | `/admin/internal-accounts` | admin |

---

## Transferências

Dono de: `payment`, `payout` (com `destination` jsonb), `payout_attempt`, o ciclo (janela
`release_at`, tarifa por `payment_method`, estados). Chama o Banco por conector; nunca FK cruzando serviço.

### Básico (infra / health)

| Prioridade | Método | Rota | Acesso |
|---|---|---|---|
| 0 | GET | `/` | público |
| 0 | GET | `/health_check` | público |

### Pagamento (venda)

| Prioridade | Método | Rota | Acesso | Justificativa |
|---|---|---|---|---|
| 1 | POST | `/payments` | cliente | Registra venda; snapshota tarifa+janela; credita in_transit. Erros: `RNV001030`, `RNV001031`, `RNV001023`. |
| 2 | GET | `/payments/{payment_key}` | cliente | Consulta pagamento; IDOR → `404 RNV001025`. |
| 2 | POST | `/payments/{payment_key}/refund` | cliente | Estorno cheio enquanto o payment está `held`; `409 RNV001026` se já `settled`, `409 RNV001003` se já estornado. Sem Idempotency-Key (estado `held`→`refunded` guarda). Contrato abaixo. |
| 3 | GET | `/payments` | cliente | Lista paginada do lojista. |

**Limite do `POST /payments`:** `amount_minor` deve ficar entre `1` e `9223372036854775807` (teto do `BIGINT`). `<= 0` ou acima do teto → `422 RNV001023`; antes desse limite o valor acima do teto virava `500`.

**`POST /payments/{payment_key}/refund` — contrato completo.**

- **Acesso:** cliente (`Authorization`). Sem corpo e **sem `Idempotency-Key`**. Não exige conta `active` do lojista: o estorno só movimenta contas internas, então `RNV001031` não se aplica.
- **Resposta `200`:** o `PaymentDTO` do payment, com `status` `refunded`.

Regra de janela por **status**, não por relógio (RFC v7.2: "o primeiro muda `held` para `refunded` ou `settled`; o segundo vê que já não é `held` e desiste"; "depois de `settled`, o estorno é recusado"):

- `held`: estorna, **mesmo que `release_at` já tenha passado** e o job ainda não tenha rodado.
- `settled`: `409 RNV001026` (valor já liberado).
- `refunded`: `409 RNV001003`.

Zona entre `release_at` e o job: enquanto o settlement não executa, o payment segue `held` e o dinheiro continua em `in_transit` (a taxa só é cobrada na liberação). Por isso o estorno ainda é possível e devolve o valor cheio. Quem decide é o status; o relógio não entra.

Idempotência: não há chave. `held → refunded` é mão única, então o retry de um estorno já feito devolve `409 RNV001003` (**não** `200`), sem novo lançamento.

Processamento:

- `FOR UPDATE` na linha do `payment` e releitura do status. Resolve a corrida estorno × settlement: o payment termina `refunded` **ou** `settled`, nunca os dois.
- Consulta a `payment_transition` antes de trocar o status.
- Lançamento no Banco, tipo `refund`, `idempotency_key` `refund:<payment_key>` e `reverses_transaction_key` = `receipt` do payment. Entries: D `in_transit` amount, C `reserves` amount (**valor cheio**, sem taxa).
- Grava `payment_status_event`.

Erros:

- `401 RNV000003`: token ausente ou inválido.
- `404 RNV001025`: payment inexistente ou de outro cliente (IDOR).
- `409 RNV001026`: payment já `settled`.
- `409 RNV001003`: payment já `refunded`.
- `503 RNV001017`: Banco indisponível ou sem resposta. O payment continua `held`; o retry é seguro (a chave `refund:<payment_key>` faz o Banco devolver o lançamento existente).

### Payout (saída de dinheiro)

| Prioridade | Método | Rota | Acesso | Justificativa |
|---|---|---|---|---|
| 1 | POST | `/payouts` | cliente | Saída externa (saque/boleto/transferência); `destination` imutável; debita a conta. |
| 2 | GET | `/payouts/{payout_key}` | cliente | Consulta saque; IDOR → `404 RNV001032`. |

**`POST /payouts` — contrato completo.**

- **Acesso:** cliente (`Authorization`). Header `Idempotency-Key` obrigatório (1 a 50 caracteres), como no `POST /payments`.
- **Corpo** (JSON Schema na porta, sem campo extra): `account_key` (UUID da conta do cliente), `purpose` (`withdrawal`, `bill_payment` ou `transfer`), `amount_minor` (inteiro) e `destination` (objeto livre, **não vazio**, no máximo 4096 bytes serializado). Não há campo obrigatório por `purpose`. `destination.scenario` é opcional (`confirm`, `refuse`, `timeout`, `flaky`) e é lido só pelo mock interbancário na reconciliação. `company_key` **não** vai no corpo: sai da conta.
- **Resposta `201`** (novo) ou **`200`** (retry): `{payout_key, company_key, account_key, purpose, destination, status, amount_minor, failure_reason, transaction_key, attempts, last_attempt_at}`. `status` nasce `pending`; `attempts` é o `COUNT` de `payout_attempt`; `last_attempt_at` é `null` até a primeira tentativa. O `destination` é gravado como enviado e **nunca muda**.
- **Autorização:** a `account_key` precisa ser de uma empresa do cliente (senão `404 RNV001018`, sem distinguir inexistente de alheia) e estar `active` (senão `403 RNV001031`). `RNV001030` não se aplica aqui: a conta é identificada pela `account_key`, e empresa sem conta nunca tem uma.
- **Processamento:** o `INSERT` do `payout` (com `idempotency_key` e `payload_hash`, `UNIQUE(company_key, idempotency_key)`) é a primeira escrita. Depois o Banco recebe o lançamento tipo `payout`, `pending`, chave `payout:<company_key>:<chave>`: D conta do cliente `amount_minor`, C `in_transit` `amount_minor` (saldo conferido sob trava no Banco). Grava `transaction_key`, `payout_status_event` e dá o commit. **Não** chama o mock interbancário: quem executa a saída é `POST /internal/payouts/reconcile`.
- **Hash do pedido:** `account_key`, `purpose`, `amount_minor` e `destination` (JSON canônico, ordem das chaves irrelevante; inclui `destination.scenario`).
- **Idempotência:** mesma chave e mesmo conteúdo devolve o estado **atual** do payout com `200`; conteúdo diferente, `422 RNV001024`. Falha antes do commit (saldo, Banco fora) dá rollback e libera a chave.

Erros:

- `400 RNV000001`: corpo fora do schema, `destination` vazio/acima de 4096 bytes, `purpose` ou `scenario` fora da lista, header ausente.
- `401 RNV000003`: token ausente ou inválido.
- `403 RNV001031`: conta não `active`.
- `404 RNV001018`: conta inexistente ou de outro cliente (mesmo código de empresa inexistente: a conta é identificada pela empresa do cliente).
- `422 RNV001023`: `amount_minor` <= 0 ou acima de 9223372036854775807.
- `422 RNV001024`: `Idempotency-Key` reusada com conteúdo diferente.
- `422 RNV001006`: saldo insuficiente, **repassado do Banco** (mesmo código; o payout não é gravado e a chave fica livre). Outros `422` de negócio do ledger também são repassados como vêm.
- `503 RNV001017`: Banco indisponível ou sem resposta; retente com a mesma chave (o lançamento `payout:<company_key>:<chave>` é deduplicado no Banco).

**`GET /payouts/{payout_key}` — contrato completo.**

- **Acesso:** cliente. Leitura passa com conta `blocked`/`closed`.
- **Resposta `200`:** o mesmo corpo do `POST`, com `status` e `attempts` atuais.
- **`404 RNV001032`:** payout inexistente, chave malformada ou de empresa de outro cliente (IDOR).

### Internal (jobs)

| Prioridade | Método | Rota | Acesso | Justificativa |
|---|---|---|---|---|
| 1 | POST | `/internal/settlements` | serviço | Job de liberação: in_transit → cliente ao fim da janela. |
| 2 | POST | `/internal/payouts/reconcile` | serviço | Job de reconciliação do payout (confirma/falha; reversal ao falhar). |
| 2 | PUT | `/internal/payment-methods/{method}` | serviço | Define taxa e janela de um meio de pagamento, versionando (append-only). |
| 2 | GET | `/internal/accounts/{account_key}/in-flight` | serviço | Valores em voo da conta: `{"held_payments": n, "pending_payouts": n}`. Chamado pelo Banco no `POST /accounts/{key}/close`. |

**`GET /internal/accounts/{account_key}/in-flight`:** só `INTERNAL-TOKEN` (`403 RNV000002` sem ele). `200` sempre que autorizado, inclusive para `account_key` desconhecida ou malformada (`{"held_payments": 0, "pending_payouts": 0}`): é contagem, não recurso. `held_payments` = payments `held` da conta; `pending_payouts` = payouts `pending`. `refunded`/`settled`/`failed` não contam.

**`PUT /internal/payment-methods/{method}` — contrato completo.**

- **Acesso:** só `INTERNAL-TOKEN`; sem ele, `403 RNV000002`.
- **`{method}`:** `pix`, `boleto` ou `card`. Fora do enum → `400 RNV000001`.
- **Corpo** (JSON Schema na porta, ambos obrigatórios, sem campo extra): `{"fee_bps": <int 0..10000>, "release_window_hours": <int 0..8760>}`. Tipo errado, campo ausente, campo extra ou valor fora da faixa → `400 RNV000001`.
- **Resposta:** `{"method", "version", "fee_bps", "release_window_hours", "created_at"}`.
  - `201`: os valores diferem da versão atual e uma **nova versão** foi gravada.
  - `200`: os valores são **iguais** aos da versão atual; nada é gravado e a resposta é a versão atual (idempotente).

Versionamento:

- **Append-only:** nunca há `UPDATE` em `payment_method`. Cada mudança grava uma nova linha com `version` incrementada; a versão **atual** é a de maior `version`.
- **Concorrência:** escritas simultâneas no mesmo método são serializadas por lock na linha da versão atual, então a comparação "igual à atual?" e o incremento de `version` não correm em paralelo.
- **Snapshot no `payment`:** o `payment` guarda a versão usada (FK para a linha de `payment_method`) e **copia** `fee_bps` e `release_at`. Mudar o método **nunca** altera payments já criados nem o que é cobrado deles: cobra-se a taxa informada ao cliente na venda. O settle continua usando só o snapshot.
- **Teto de `release_window_hours` (8760 h, 1 ano):** decisão de projeto. Protege contra overflow de data no cálculo de `release_at` e fica muito acima da maior janela atual (720 h).
- **`fee_bps <= 10000`:** também é `CHECK` na tabela. Sem ele, `fee_bps` acima de 10000 faria o cálculo da tarifa (`split_fee`) levantar `ValueError`, o que daria `500` e abortaria o run inteiro do job de settlement.

**`as_of` nos jobs.** Os dois endpoints aceitam corpo opcional para injetar o "agora", de modo que testes e operação não precisem esperar a janela (24h/72h/720h) nem o backoff:

```json
{"as_of": "2026-10-12T12:00:00-03:00"}
```

- **Ausente** (corpo vazio ou sem a chave) = relógio do servidor.
- **Formato:** ISO 8601 **com fuso** (offset ou `Z`). Sem fuso ou não-ISO → `400 RNV000001` (JSON Schema na porta, antes de qualquer consulta).
- **Acesso:** só existe em `/internal/*` (`INTERNAL-TOKEN`; sem ele, `403 RNV000002`). **Nunca** é aceito em rota de cliente: serve a testes e operação, não ao produto.
- **`POST /internal/settlements`:** libera os `payment` em `held` com `release_at <= as_of`. A chave determinística (`settlement:<payment_key>`) e o `FOR UPDATE` na linha do `payment` continuam valendo; rodar de novo com o mesmo `as_of` é no-op.
- **`POST /internal/payouts/reconcile`:** `as_of` é o "agora" que decide se a próxima tentativa/backoff do payout já venceu (`last_attempt_at` + espera) e o `now` gravado ao registrar a `payout_attempt`.

**`POST /internal/settlements` — contrato completo.**

Resposta `200`:

```json
{"as_of": "2026-10-12T15:00:00+00:00", "settled": ["<payment_key>"], "deferred": ["<payment_key>"]}
```

- `as_of`: o instante efetivamente usado (o enviado, ou o relógio do servidor se ausente), ISO 8601.
- `settled`: `payment_key` dos payments liberados neste run.
- `deferred`: payments vencidos (`release_at <= as_of`) que **continuam `held`** porque o Banco recusou por regra (ex.: conta do lojista bloqueada ou encerrada, `RNV001005`) ou estava indisponível. O próximo run tenta de novo.
- Payment que, ao ser relido, já não está `held` (já liberado ou estornado) não aparece em nenhuma lista. Não há lista de erros por item.

Processamento:

- Cada payment roda em **transação própria**: um lojista com problema não trava os demais.
- A tarifa vem **sempre do snapshot** do payment: `fee = (amount_minor * fee_bps + 9999) // 10000`, `net = amount_minor - fee`.
- Lançamento no Banco com `idempotency_key` `settlement:<payment_key>`: D `in_transit` net, D `in_transit` fee, C conta do lojista net, C `revenue` fee. Pernas de valor 0 são **omitidas** (o Banco exige >= 1 por perna; ex.: `amount_minor` 1 com 99 bps dá fee 1 e net 0, então só existem as pernas de fee).

Erros do job:

- `403 RNV000002`: sem `INTERNAL-TOKEN`.
- `400 RNV000001`: `as_of` inválido.
- Falhas do Banco por item **não** viram erro HTTP: o payment vai para `deferred`.

Idempotência: rodar de novo é seguro. A chave é determinística; o Banco devolve o lançamento existente e o payment é levado a `settled`.

**`POST /internal/payouts/reconcile` — contrato completo.**

- **Acesso:** só `INTERNAL-TOKEN`; sem ele, `403 RNV000002`.
- **Corpo opcional** (JSON Schema na porta): `{"as_of": "<ISO 8601 com fuso>"}`; sem campo extra. `as_of` inválido → `400 RNV000001`.
- **Resposta `200`:** `{"as_of": "<instante usado>", "settled": [payout_key], "failed": [payout_key], "pending": [payout_key]}`.
  - `settled`: payouts levados a `settled` neste run.
  - `failed`: payouts levados a `failed` neste run (a reversal já está no Banco).
  - `pending`: payouts **tratados neste run** que continuam `pending`: ou o interbancário não respondeu e ainda há tentativas, ou o Banco recusou/ficou indisponível no settlement/reversal (próximo run retoma).
  - Payout que não foi tocado (ainda dentro do backoff, ou já não `pending` ao ser relido) **não aparece** em nenhuma lista. Não há lista de erros por item.
- **Configuração (env, serviço Transferências):** `PAYOUT_MAX_ATTEMPTS=3`; `PAYOUT_BACKOFF_BASE_SECONDS=60`; `PAYOUT_MAX_PER_RUN=50`; `INTERBANK_API_URL`; `INTERBANK_TIMEOUT_SECONDS=5`.
- **Backoff:** exponencial dobrando a partir de `PAYOUT_BACKOFF_BASE_SECONDS`, medido de `last_attempt_at` até `as_of`: espera de 60 s após a 1ª tentativa, 120 s após a 2ª. Tentativa só acontece com `as_of >= last_attempt_at + espera`; antes disso o payout fica de fora (sem nova `payout_attempt`). `last_attempt_at` e o `created_at` da `payout_attempt` recebem `as_of`.
- **Teto por run:** no máximo `PAYOUT_MAX_PER_RUN` payouts acionáveis por chamada, em ordem de `last_attempt_at` (nulos primeiro) e `id`. O resto fica para o próximo run.
- **Tentativa:** cada chamada ao mock é uma linha append-only em `payout_attempt` (`attempt_number = COUNT + 1`, resultado `confirmed|rejected|timeout`), commitada antes de qualquer lançamento no Banco. O corpo enviado ao mock é exatamente `{payout_key, amount_minor, purpose, destination}`.
- **Classificação do interbancário** (`connectors/interbank_connector.py`): `200` = `confirmed`; `422` com `status: refused` = `rejected`; timeout de rede, erro de conexão, `504` e qualquer outra resposta (inclusive `4xx`/`5xx` inesperados) = `timeout` (resultado inconclusivo, que se retenta e, esgotado o limite, se desfaz por reversal; é o caminho seguro para o dinheiro do lojista). O caso inesperado é logado.

**Máquina de fases do payout `pending`.** A fase é derivada da última `payout_attempt` (e do `COUNT`), nunca de um campo mutável; a linha do `payout` é travada (`SELECT ... FOR UPDATE`, READ COMMITTED) e o status relido antes de cada passo, em transação própria por passo:

| Estado derivado | Fase | O que faz | Se der certo | Se o Banco recusar/cair |
|---|---|---|---|---|
| 0 tentativas, ou último `timeout` com tentativas < 3 e backoff vencido | `attempt` | chama o mock, grava a `payout_attempt`, commit | `confirmed` → fase `settle`; `rejected` → fase `reverse`; `timeout` com tentativas sobrando → fica `pending` (aparece em `pending`); 3º `timeout` → fase `reverse` | (não fala com o Banco) |
| último `confirmed` | `settle` | lançamento `settlement:<payout_key>` (D `in_transit` / C `reserves`, `settles_transaction_key` = `transaction_key` do payout) | payout `settled` (`payout_transition` + `payout_status_event`, razão `settlement`) | continua `pending`, aparece em `pending`; próximo run repete só o settlement, **sem chamar o mock** |
| último `rejected`, ou 3 tentativas com último `timeout` | `reverse` | lançamento `reversal:<payout_key>` (D `in_transit` / C conta do cliente, `reverses_transaction_key` = `transaction_key` do payout) | payout `failed` com `failure_reason` `interbank_refused` ou `interbank_timeout` | continua `pending` (ex.: conta bloqueada, `RNV001005`); próximo run repete só a reversal, **sem chamar o mock** |

- `failed` só é gravado **junto** da reversal bem-sucedida (ou reencontrada pela chave determinística, que o Banco deduplica). Nunca existe payout `failed` sem reversal.
- A `transaction` payout original continua `pending` no livro quando há reversal; quem a desfaz é a reversal (`reverses_transaction_id`). No settlement ela vai a `settled`.
- Fases `settle` e `reverse` **não** esperam backoff (não chamam o mock).
- **Concorrência:** dois runs simultâneos serializam no lock do payout; quem chega depois relê o estado e não faz tentativa dupla nem lançamento dobrado (as chaves `settlement:`/`reversal:` são determinísticas e `UNIQUE(payout_id, attempt_number)` é a rede de proteção).
- **Idempotência:** rodar de novo é seguro; payout `settled`/`failed` nunca é reprocessado.
- **Custo do lock:** a linha do payout e a conexão do banco ficam presas durante a chamada ao mock (até `INTERBANK_TIMEOUT_SECONDS`, 5 s); ver `limites-e-evolucao.md`.

O mock interbancário que o reconcile chama (`POST /interbank/transfers` no `external-mocks`) está em `mocks-externos.md`.

### Admin

| Prioridade | Método | Rota | Acesso |
|---|---|---|---|
| 3 | GET | `/admin/payments` | admin |

---

## Sugestões incorporadas (refino da v7)

- `POST /accounts/{account_key}/close` só encerra com **saldo zero e nada em trânsito** (`422 RNV001035` caso contrário; `503 RNV000006` se o Transferências estiver fora).
- `GET /admin/internal-accounts` para auditar as três contas internas (reserves / in_transit / revenue).
- `GET /payouts/{payout_key}` para o lojista acompanhar o saque.
- Novos códigos: `RNV001030` (empresa sem conta aberta), `RNV001031` (conta não active, só escrita),
  `RNV001032` (saque inexistente ou de outro lojista).
- `as_of` opcional no corpo de `POST /internal/settlements` e `POST /internal/payouts/reconcile`: refino
  em cima da RFC v7.2, que não menciona `as_of` (ela fala só em "o relógio" e "quando `release_at` vence").
  Sem o campo, nada muda; existe para testar sem esperar a janela. Só com `INTERNAL-TOKEN`.
  Em operação, o prazo definido nas tabelas (`release_window_hours` do `payment_method`) é o que prevalece.
- `PUT /internal/payment-methods/{method}`: versiona taxa e janela (append-only); a RFC v7.2 trata `payment_method` como tabela com snapshot no `payment`, mas não cita a rota nem o versionamento.
