# Checkup de testes

Retrato da suíte em **2026-10-12**, com a reconciliação de recebimento sem venda incluída. Todos os testes são de integração caixa-preta: falam com as APIs por HTTP, como um cliente, e nunca importam código de `src/`. Cada rota nasceu de um teste que falhou primeiro (TDD).

## 1. Resumo

| Serviço | Testes | Dos quais `fault` | Dos quais `slow` |
|---|---|---|---|
| Banco | 419 | 2 | 0 |
| Transferências | 409 | 13 | 14 |
| external-mocks | 36 | 0 | 0 |
| **Total** | **864** | **15** | **14** |

Além da suíte, a coleção [`docs/postman/rnv-ponta-a-ponta.postman_collection.json`](postman/rnv-ponta-a-ponta.postman_collection.json) roda a história completa (cadastro → vendas → estorno → liberação → saques → encerramento → auditoria) com 40 requisições e 66 asserções, inclusive os saldos em cada passo e a equação do livro.

**Como rodar** (stack de pé com `docker compose up -d`, venv da raiz ativo):

| Comando | O que roda |
|---|---|
| `pytest` | tudo, menos `fault` (o `pytest.ini` da raiz aplica `-m "not fault"`) |
| `pytest -m "not fault and not slow"` | pula também os que esperam o timeout real do interbancário (~5 s cada) |
| `docker compose --profile fault up -d` e `pytest -m fault` | falhas de infraestrutura: Banco fora, Transferências fora, pool esgotado |
| `npx newman run docs/postman/rnv-ponta-a-ponta.postman_collection.json` | a coleção ponta a ponta |

Um `-m` passado na linha de comando **substitui** o do `pytest.ini`: `pytest -m "not slow"` sozinho volta a coletar os testes `fault`, que falham sem o profile.

## 2. Mapa da suíte

| Serviço | Área | Testes | O que cobre |
|---|---|---|---|
| Banco | `account` | 115 | abertura com birô, consulta, saldo e saldo formatado, extrato com cursor e período, bloqueio, encerramento com in-flight |
| Banco | `admin` | 72 | acesso, listas paginadas, filtro de status, totais e equação do livro |
| Banco | `auth` | 16 | `/auth/me` para o Transferências |
| Banco | `client` | 42 | cadastro, CPF, idade, e-mail, formato e tradução dos erros |
| Banco | `company` | 29 | cadastro, CNPJ, posse |
| Banco | `internal_accounts` | 6 | contas internas |
| Banco | `ledger` | 98 | fechamento, tipos e referências, consumo único, saldo sob trava, limites, idempotência, mesma conta nos dois lados, recebimentos em aberto, `reversed` no replay |
| Banco | `middleware` e handlers | 41 | `INTERNAL-TOKEN`, token de cliente, `X-Request-ID`, 404/405, health |
| Transferências | `payment` | 47 | criação, autorização, validação, limites, idempotência, recibo no Banco |
| Transferências | `refund` | 20 | estorno por status, corrida com a liberação, Banco fora |
| Transferências | `payment_list` | 34 | listagem, filtros, cursor assinado |
| Transferências | `payment_method` | 43 | versionamento append-only, snapshot da taxa e da janela |
| Transferências | `settlement` | 31 | liberação, tarifa arredondada para cima, `deferred`, idempotência, corrida |
| Transferências | `payout` | 67 | criação, autorização, validação, idempotência, saldo insuficiente repassado |
| Transferências | `reconcile` | 49 | confirmação, recusa, timeout com backoff, `flaky`, teto por run, corrida, conta bloqueada, Banco fora |
| Transferências | `receipt_reconcile` | 17 | recebimento sem venda: carência, estorno, retry tardio recusado, ledger fora |
| Transferências | `in_flight` | 12 | contagem em voo e encerramento barrado |
| Transferências | `admin` | 42 | `/admin/payments`, acesso, filtros combinados |
| Transferências | `middleware` e handlers | 47 | autenticação via Banco, `INTERNAL-TOKEN`, `X-Request-ID`, 404/405, health |
| external-mocks | interbancário e health | 36 | os cenários `confirm`, `refuse`, `timeout`, `flaky` e a validação do corpo |

## 3. Testes obrigatórios do CLAUDE.md

| Obrigatório | Teste |
|---|---|
| Dois débitos simultâneos: um passa, um `422`, saldo nunca negativo | `test_concurrent_debits_never_overdraw` (`ledger/test_ledger_transaction_create.py`), `test_refuses_duplicate_debits_exceeding_balance` e `test_opposite_order_debits_never_deadlock` (`ledger/test_ledger_concurrency_edge.py`) |
| N créditos simultâneos: todos entram, saldo = soma | `test_concurrent_credits_all_add_up` (`account/test_account_balance.py`) |
| 10x a mesma `Idempotency-Key`: uma operação | `test_concurrent_replays_create_a_single_payment`, `test_concurrent_requests_create_one_payment_and_one_receipt`, `test_concurrent_requests_create_one_payout_and_one_debit`, `test_concurrent_replays_create_one_transaction` |
| Taxa snapshotada: muda a taxa entre a chegada e a liberação, cobra a antiga | `test_settlement_charges_the_old_fee_after_the_fee_changed` e `test_changing_the_window_does_not_move_an_existing_release_at` (`payment_method/test_payment_method_snapshot.py`) |
| Estorno cheio na janela; recusado depois de `settled` | `test_refunds_a_held_payment`, `test_bank_holds_the_full_amount_refund_under_the_refund_key`, `test_settled_payment_cannot_be_refunded` (`refund/test_payment_refund.py`) |
| 3 timeouts de payout → `failed` + reversal devolve o dinheiro | `test_third_timeout_fails_the_payout`, `test_reversal_entry_exists_in_the_bank` e `test_the_money_returns_to_the_account` (`reconcile/test_payout_reconcile_timeout.py`, `reconcile/test_payout_reconcile_refuse.py`) |

## 4. Concorrência e falha de infraestrutura

**Corridas cobertas** (cada uma termina com um único vencedor e o livro fechando):

| Corrida | Teste |
|---|---|
| dois débitos na mesma conta | `test_concurrent_debits_never_overdraw` |
| dez estornos do mesmo payment | `test_ten_simultaneous_refunds_yield_a_single_success` |
| estorno × job de liberação | `test_refund_racing_the_settlement_job_has_a_single_winner` |
| dois runs do job de liberação | `test_concurrent_runs_release_the_payment_exactly_once` |
| dois runs do reconcile | `test_simultaneous_runs_settle_a_payout_once`, `test_simultaneous_runs_make_a_single_attempt` |
| duas liquidações do mesmo payout | `test_concurrent_settlements_settle_payout_once` |
| duas aberturas de conta para a mesma empresa | `test_concurrent_requests_open_a_single_account` |
| dois bloqueios da mesma conta | `test_concurrent_blocks_let_only_one_through` |
| mesmo CPF ou CNPJ ao mesmo tempo | `test_concurrent_registrations_with_same_cpf_create_a_single_client`, `..._same_cnpj_create_a_single_company` |
| duas mudanças iguais de tarifa | `test_concurrent_identical_changes_create_exactly_one_version` |

**Falhas de infraestrutura** (`-m fault`, com um proxy que derruba o ledger e uma instância com pool mínimo): Banco fora no `POST /payments` e no estorno (`503 RNV001017`, nada gravado, retry seguro); ledger fora no job de liberação, no reconcile e na reconciliação de recebimentos (item em `deferred`, o próximo run conclui); pool esgotado (`503 RNV000006`); Transferências fora no encerramento da conta (`503 RNV001036`, conta continua `active`).

## 5. Bugs encontrados por checkups

| Data | Falha | Antes | Depois | Teste que trava |
|---|---|---|---|---|
| 2026-10-11 | `debit_minor`/`credit_minor` acima de `9223372036854775807` no ledger | `500` (estouro de `BIGINT`) | `400 RNV000010` | `test_ledger_limits.py` |
| 2026-10-11 | `amount_minor` acima do teto no `POST /payments` | `500` | `422 RNV001023` | `test_payment_amount_limits.py` |
| 2026-10-11 | `entries` sem limite (2001 pernas aceitas) | `201` | `400 RNV000010` acima de 20 | `test_refuses_more_than_max_entries` |
| 2026-10-12 | Erro de parâmetro de query dizia `body:` na descrição | descrição enganosa | aponta `query:` ou o nome do campo | `test_unknown_parameter_error_points_to_the_query` (4 rotas) |
| 2026-10-12 | Débito e crédito na mesma conta aceitos pelo ledger | `201` | `422 RNV001037` | `test_ledger_same_account.py` |
| 2026-10-12 | Recebimento sem venda ficava parado no Trânsito | sem correção | estornado pela reconciliação | `receipt_reconcile/` |

## 6. Lacunas conhecidas

| Lacuna | Detalhe |
|---|---|
| Erro `500` não tratado | Uma exceção inesperada sai como `Internal Server Error` em texto puro, fora do formato `{title, description, translation, code}`. Não há handler genérico de `Exception`. |
| Corrida retry tardio × reconciliação de recebimentos | Janela de milissegundos, depois de 24 h de carência, em que um retry pode criar um `payment` sobre um recebimento estornado. Documentada em `limites-e-evolucao.md`; sem teste, porque depende de intercalar duas requisições num ponto exato. |
| Agendamento dos jobs | Liberação, reconcile e reconciliação de recebimentos só rodam quando alguém chama a rota; os testes chamam com `as_of`. |
| Interbancário real | O simulador nunca perde uma resposta depois de pagar; o caso "pagou e a resposta se perdeu" não é testável aqui. |
