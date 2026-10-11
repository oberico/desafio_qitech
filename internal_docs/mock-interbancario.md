# Mock do interbancário — contrato

> Doc canônico do serviço `interbank-mock/` (porta **8003**). Simula o sistema externo que
> executa a saída do dinheiro (passo 7 da RFC v7.2). Não é dono de dado nenhum: não fala com o
> Banco nem com o Transferências, só responde quando chamado. **Sem autenticação** (é um sistema
> externo simulado). Estado **em memória**; reiniciar o container zera tudo.

## Quem chama

O Transferências, em `connectors/interbank_connector.py`, durante `POST /internal/payouts/reconcile`.
URL base na env `INTERBANK_API_URL` (ex.: `http://interbank-mock:8003`). Cada chamada vira uma linha
em `payout_attempt` (resultado `confirmed`, `rejected` ou `timeout`).

## Rotas

### `GET /health_check`

`204`, sem corpo.

### `POST /transfers`

Corpo (JSON Schema; qualquer desvio → `400 RNV000001`):

| Campo | Tipo | Regra |
|---|---|---|
| `payout_key` | string | UUID v4 |
| `amount_minor` | integer | `> 0` |
| `purpose` | string | obrigatório |
| `destination` | objeto | livre; só `destination.scenario` é lido |

`destination.scenario` é opcional: `confirm` (padrão), `refuse`, `timeout`, `flaky`. Valor fora da lista → `400 RNV000001`.

| Cenário | Resposta |
|---|---|
| ausente / `confirm` | `200 {"transfer_id": "<uuid>", "status": "confirmed"}` |
| `refuse` | `422 {"status": "refused", "reason": "destination_refused"}` |
| `timeout` | sem resposta em tempo útil (a conexão fica pendurada além do timeout do conector) |
| `flaky` | para o mesmo `payout_key`: 1ª e 2ª chamadas = `timeout`; da 3ª em diante = `confirm` |

**Idempotência por `payout_key`:** repetir a chamada de um transfer já confirmado devolve o **mesmo** `transfer_id`. O contador do `flaky` também é por `payout_key`.

## Cenário → efeito no payout e no livro

Ponto de partida (passo 6): `payout` `pending`, `transaction` payout `pending` (D Cliente / C Trânsito). O limite de 3 tentativas é configuração; o número de tentativas é `COUNT` de `payout_attempt`.

| Cenário | Resultado da tentativa | `payout_status` | Livro |
|---|---|---|---|
| `confirm` | `confirmed` | `pending → settled` | passo 7: D Trânsito / C Caixa; a `transaction` payout vai `pending → settled` |
| `refuse` | `rejected` | `pending → failed` na hora, sem retentar | `transaction` reversal (`reverses_transaction_id` → payout): D Trânsito / C Cliente; a payout original continua `pending` |
| `timeout` | `timeout` nas 3 tentativas | `pending` com backoff crescente após a 1ª e a 2ª; na 3ª sem resposta `→ failed` | idem `refuse`: a reversal devolve o dinheiro ao lojista |
| `flaky` | `timeout`, `timeout`, `confirmed` | `pending` após as 2 primeiras; `→ settled` na 3ª | como `confirm` na 3ª; nenhuma reversal. Prova que retry + backoff funcionam sem perder o payout |

Ver RFC v7.2 §2, passos 6-7 e "Caminhos alternativos" (mock sem resposta, recusa definitiva). Com `as_of` (ver `rotas.md`), os testes avançam o backoff entre as chamadas de reconcile sem esperar.

## Limites aceitos

- Estado em memória: reiniciar o mock zera os `transfer_id` e o contador do `flaky`.
- O risco "pagou, mas a resposta se perdeu" não existe aqui (RFC §2, perguntas de estresse): o mock nunca confirma e some.
