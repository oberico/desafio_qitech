# Checkup de testes e casos de borda

## 1. Resumo

Em **2026-10-11** foi feito um checkup da suíte de testes e dos casos de borda das APIs (Banco e Transferências) e do mock (`external-mocks`). Resultado:

- 2 bugs reais, ambos respondiam `500` por estouro de `BIGINT` (valor acima de `9223372036854775807`).
- 1 lacuna de validação: `entries` sem `maxItems` (2001 entradas aceitas).
- 1 teste obrigatório do `CLAUDE.md` sem cobertura possível hoje (taxa snapshotada) e 3 dependentes de fatias pendentes.
- Os 3 achados foram corrigidos na branch `fix/amount-bounds-and-edge-tests`.

Estado medido **antes** dos novos testes desta branch.

## 2. Mapa de testes

Totais executados (incluem casos parametrizados): Banco 195, Transferências 108 (+ 6 `fault`), `external-mocks` 36. A coluna "funções" conta as funções `test_*` por área (menor que o total executado quando há parametrização); as 6 `fault` não entram nessa contagem.

### Banco (195)

| Área | Pasta (`banco/tests/integration/`) | Funções |
|---|---|---|
| Cliente | `client/` | 20 |
| Empresa | `company/` | 18 |
| Conta (abrir, consultar, encerrar) | `account/test_account_{open,get,close}.py` | 28 |
| Conta (bloqueio e desbloqueio) | `account/test_account_block*.py`, `test_account_unblock.py` | 20 |
| Auth (`/auth/me`) | `auth/` | 14 |
| Ledger (criação, settlement) | `ledger/` | 36 |
| Contas internas | `internal_accounts/` | 6 |
| Middleware e infra (token, contexto, erros, health) | `middleware/`, `test_error_handlers.py`, `test_health_check.py` | 17 |

### Transferências (108 + 6 `fault`)

| Área | Pasta (`transferencias/tests/integration/`) | Funções |
|---|---|---|
| Payment (criar, validar, autorizar, idempotência, ledger, consulta, Banco fora, serviço ocupado) | `payment/` | 32 |
| Settlement (liberação, deferred, idempotência, validação, acesso, Banco fora) | `settlement/` | 17 |
| Middleware e infra | `middleware/`, `test_error_handlers.py`, `test_health_check.py` | 20 |

### external-mocks (36)

| Área | Arquivo | Funções |
|---|---|---|
| `POST /interbank/transfers` | `test_post_transfer.py` | 14 |
| Health | `test_health_check.py` | 4 |

## 3. Testes obrigatórios do CLAUDE.md

| Teste obrigatório | Estado | Observação | Status |
|---|---|---|---|
| Dois débitos simultâneos (um passa, um `422`, saldo nunca negativo) | ✅ coberto | | feito |
| 10x a mesma Idempotency-Key (uma operação) | ✅ coberto | | feito |
| N créditos simultâneos (todos entram, saldo = soma) | ⏳ pendente | Depende do `GET /accounts/{key}/balance` (item B1 pendente) | futuro |
| Taxa snapshotada (muda a taxa entre chegada e liberação, cobra a antiga) | ✅ coberto | Via `PUT /internal/payment-methods/{method}`; testes em `transferencias/tests/integration/payment_method/` (branch `feature/payment-method-versioning`); `test_payment_method_snapshot.py::test_settlement_charges_the_old_fee_after_the_fee_changed` e `test_changing_the_window_does_not_move_an_existing_release_at` | feito |
| Estorno cheio na janela, recusado depois de `settled` | ✅ coberto | Branch `feature/payment-refund`; `refund/test_payment_refund.py`: `test_refunds_a_held_payment`, `test_settled_payment_cannot_be_refunded`, `test_second_refund_is_refused`, `test_ten_simultaneous_refunds_yield_a_single_success` e `test_refund_racing_the_settlement_job_has_a_single_winner` | feito |
| 3 timeouts de payout viram `failed` + reversal devolve o dinheiro | ⏳ pendente | Slice T6 (reconcile do payout) | futuro |

## 4. Casos de borda sondados

### Comportou-se bem

| Caso | Resultado |
|---|---|
| Idempotency-Key com 100 caracteres | aceita |
| Idempotency-Key com 101 caracteres | recusada (`400 RNV000001`) |
| Idempotency-Key vazia | recusada (`400 RNV000001`) |
| `account_key` e `company_key` em maiúsculas | aceitos |
| Dois débitos na mesma conta dentro de uma transação | somam |
| 400 débitos simultâneos em ordem oposta entre duas contas | sem deadlock (trava pelo id menor); agora travado por `test_ledger_concurrency_edge.py::test_opposite_order_debits_never_deadlock` |
| Job de settlement com corpo array, string ou JSON quebrado | recusado (`400 RNV000001`) |
| Job de settlement com `as_of` nulo, offset `+99:99` ou data impossível | recusado (`400 RNV000001`) |
| Job de settlement com `as_of` no ano 0001 e no ano 9999 | aceito |

### Falhou

| # | Falha | Antes | Depois | Status | Teste que trava |
|---|---|---|---|---|---|
| 1 | Banco `POST /ledger/transactions` com `debit_minor`/`credit_minor` acima de `9223372036854775807` | `500` (estouro de BIGINT) | `400 RNV000001` | corrigido na branch `fix/amount-bounds-and-edge-tests` | `test_ledger_limits.py`: `test_refuses_debit_above_bigint`, `test_refuses_credit_above_bigint`, `test_refuses_balanced_entries_above_bigint` e `test_accepts_exact_bigint_limit` |
| 2 | Transferências `POST /payments` com `amount_minor` acima de `9223372036854775807` | `500` | `422 RNV001023` | corrigido na branch `fix/amount-bounds-and-edge-tests` | `test_payment_amount_limits.py`: `test_refuses_amount_above_bigint` e `test_accepts_exact_bigint_limit` |
| 3 | `entries` sem `maxItems` (2001 entradas aceitas) | `201` | `400 RNV000001` acima de 20 | corrigido na branch `fix/amount-bounds-and-edge-tests` | `test_ledger_limits.py`: `test_refuses_more_than_max_entries` e `test_accepts_exactly_max_entries` |

## 5. Decisões de contrato registradas

| Decisão | Rota | Erro |
|---|---|---|
| `debit_minor`/`credit_minor` de `1` a `9223372036854775807` (teto do BIGINT) | Banco `POST /ledger/transactions` | `400 RNV000001` (JSON Schema) |
| `entries` de `2` a `20` itens (transação real tem no máximo 4) | Banco `POST /ledger/transactions` | `400 RNV000001` |
| `amount_minor` acima de `9223372036854775807` | Transferências `POST /payments` | `422 RNV001023` (código existente, que já cobria `<= 0`) |
| `POST /payments/{payment_key}/refund` decide pelo **status**, não pelo relógio: estorna enquanto `held` (mesmo após `release_at`, antes do job); `settled` recusa. Sem `Idempotency-Key`: `held → refunded` é mão única e o retry devolve `409` | Transferências `POST /payments/{payment_key}/refund` | `409 RNV001026` (já `settled`), `409 RNV001003` (já `refunded`), `404 RNV001025`, `503 RNV001017` |
| `PUT /internal/payment-methods/{method}` versiona (append-only) em vez de `UPDATE`; valores iguais à versão atual não criam versão (`200`), mudança cria (`201`) | Transferências `PUT /internal/payment-methods/{method}` | `400 RNV000001` (JSON Schema), `403 RNV000002` |

Documentadas em `rotas.md` e `catalogo-de-erros.md`. Nenhum código novo foi criado.

**Por que versionar e não dar `UPDATE` no `payment_method`:**

- O preço informado ao cliente na venda prevalece: mudar a tabela nunca altera o que foi cobrado de payments já criados.
- Histórico não se apaga (append-only, mesma regra do resto do sistema); `UPDATE` destruiria a prova de qual taxa valia em cada data.
- Rastreabilidade: o `payment` guarda FK para a versão usada e copia `fee_bps` e `release_at` (snapshot), então dá para provar a origem de cada cobrança.
- Limites de projeto: `release_window_hours <= 8760` (1 ano; evita overflow de data, muito acima dos 720 h atuais) e `fee_bps <= 10000` (`CHECK` e JSON Schema).

## 6. Documentos a atualizar no futuro

| Documento | O que falta | Dono / slice | Status |
|---|---|---|---|
| `rotas.md` | Limites de valor e de `entries` | Hann | feito |
| `catalogo-de-erros.md` | `RNV001023` cobre valor acima do teto | Hann | feito |
| `insomnia-banco.json` | Defasado: sem conta, ledger, bloqueio | Chaz | futuro |
| `insomnia-banco-ledger.json` | Sem block/unblock e sem limites de valor | Chaz | futuro |
| `insomnia-transferencias.json` | Refund (T3), payouts (T4-T6) | Chaz, slices T3-T6 | futuro |
| `rfc-rnv-v7.2.md` | Vai **absorver** `as_of` (existe só para fins de teste; em operação prevalece o prazo das tabelas, `release_window_hours` do `payment_method`) e o `external-mocks` (faz parte do negócio, ainda não está na RFC). Também precisa citar o versionamento de `payment_method` e a rota `PUT /internal/payment-methods/{method}`. Os limites de BIGINT seguem sem menção | Usuário/grupo | decidido, falta escrever |
| `analise-defesa-rfc.md` | Acrescentar os limites conhecidos | Hann | futuro |
| `rotas.md` | `GET balance`/`statement` quando existirem; corpo do job de reconcile | Hann, após B1 e T6 | futuro |
| `catalogo-de-erros.md` | Novos códigos de payout (criar só com aprovação do usuário) | Hann, slices T4-T6 | futuro |
| `CLAUDE.md` | Testes obrigatórios que ficaram sem cobertura caixa-preta (taxa snapshotada e demais pendentes da seção 3) | Usuário | futuro |

### Pendências conhecidas (não são bugs corrigidos)

| Pendência | Detalhe | Status |
|---|---|---|
| Reconciliação Transferências × Banco | `receipt` órfão: lançamento no Banco sem `payment` correspondente se a escrita local falhar depois | futuro |
| `D X + C X` na mesma conta com saldo zero | Comportamento não definido e não testado | futuro |
| Job de settlement global | Duração cresce com o tamanho da base; ver `limites-e-evolucao.md` | futuro |
| `fee_bps` > 10000 faz o job de settlement dar 500 (`split_fee` levanta `ValueError` para `fee_bps` acima de 10000) | Risco latente resolvido pelo `CHECK` de `fee_bps <= 10000` e pela validação da rota `PUT /internal/payment-methods/{method}` | fechado |

> Depois dos testes novos desta branch: Banco 270 e Transferências 111 casos executados (mais 6 `fault`), external-mocks 36. Débitos duplicados na mesma conta somam: `test_refuses_duplicate_debits_exceeding_balance` e `test_accepts_duplicate_debits_within_balance`.

> Taxa versionada: Transferências 151 casos executados (mais 6 `fault`) e Banco 270.

> Com o refund (T3): Transferências 173 casos executados (mais 8 `fault`) e Banco 270.
