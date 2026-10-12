# Mocks externos — contrato

> Doc canônico do serviço `external-mocks/` (porta **8003**, env `EXTERNAL_MOCKS_PORT`). Um único container que simula os sistemas externos com que o produto conversa. As rotas são organizadas **por domínio** (`/interbank/...`, depois `/bureau/...`). Não é dono de dado nenhum: não tem banco, não fala com o Banco nem com o Transferências, só responde quando chamado. **Sem autenticação** (são sistemas externos simulados). Estado **em memória**; reiniciar o container zera tudo.

## Visão geral

- **O que é:** um servidor à parte que faz o papel de terceiros (interbancário hoje, birô depois), para o fluxo rodar de ponta a ponta sem integração real.
- **Sem auth, sem banco:** nenhum token, nenhuma tabela. Todo estado (ex.: `transfer_id` emitidos, contador do `flaky`) vive em memória.
- **Quem chama:** só os conectores dos serviços de negócio. Ninguém mais (nem o cliente final) fala com ele.
- `GET /health_check` na raiz: `204`, sem corpo.
- `MOCK_TIMEOUT_SECONDS` (=30, env do mock): quanto o mock dorme para simular "sem resposta". Fica bem acima do timeout do conector.

## Domínios

| Domínio | Prefixo | Estado | Quem chama |
|---|---|---|---|
| `interbank` | `/interbank` | ativo | Transferências, `connectors/interbank_connector.py` |
| `bureau` | `/bureau` | **planejado** | Banco (verificação de empresa) |

Birô: hoje é o `MockBureauConnector` dentro do Banco. Ele migra para o `external-mocks` numa fatia própria, ainda não feita. Até lá, este doc não define rotas de birô.

## Domínio `interbank`

Simula o sistema externo que executa a saída do dinheiro (passo 7 da RFC v7.2).

### Quem chama

O Transferências, em `connectors/interbank_connector.py`, durante `POST /internal/payouts/reconcile`. URL base na env `INTERBANK_API_URL` (ex.: `http://external-mocks:8003`). Timeout do conector na env `INTERBANK_TIMEOUT_SECONDS` (=5): sem resposta em 5s a tentativa vira `timeout`. O conector também trata como `timeout` erro de conexão, `504` e qualquer resposta fora de `200` ou `422 refused` (detalhe em `rotas.md`, `POST /internal/payouts/reconcile`). O corpo enviado é exatamente `{payout_key, amount_minor, purpose, destination}`. Cada chamada vira uma linha em `payout_attempt` (resultado `confirmed`, `rejected` ou `timeout`).

### `POST /interbank/transfers`

Corpo (JSON Schema estrito; qualquer desvio → `400 RNV000001`):

| Campo | Tipo | Regra |
|---|---|---|
| `payout_key` | string | UUID v4 |
| `amount_minor` | integer | `> 0` |
| `purpose` | string | obrigatório |
| `destination` | objeto | livre; só `destination.scenario` é lido |

Schema estrito: **campo extra na raiz do corpo é recusado** (`400 RNV000001`). Dentro de `destination` o objeto é livre.

`destination.scenario` é opcional: `confirm` (padrão), `refuse`, `timeout`, `flaky`. Valor fora da lista → `400 RNV000001`.

| Cenário | Resposta |
|---|---|
| ausente / `confirm` | `200 {"transfer_id": "<uuid>", "status": "confirmed"}` |
| `refuse` | `422 {"status": "refused", "reason": "destination_refused"}` |
| `timeout` | o mock dorme `MOCK_TIMEOUT_SECONDS` (30s), muito acima dos 5s do conector, que desiste antes; se a conexão sobreviver, o mock responde `504` |
| `flaky` | para o mesmo `payout_key`: 1ª e 2ª chamadas = `timeout`; da 3ª em diante = `confirm` |

**Idempotência por `payout_key`:** repetir a chamada de um transfer já confirmado devolve o **mesmo** `transfer_id`. O contador do `flaky` também é por `payout_key`.

### Cenário → efeito no payout e no livro

Ponto de partida (passo 6): `payout` `pending`, `transaction` payout `pending` (D Cliente / C Trânsito). O limite de 3 tentativas é configuração; o número de tentativas é `COUNT` de `payout_attempt`.

| Cenário | Resultado da tentativa | `payout_status` | Livro |
|---|---|---|---|
| `confirm` | `confirmed` | `pending → settled` | passo 7: D Trânsito / C Caixa; a `transaction` payout vai `pending → settled` |
| `refuse` | `rejected` | `pending → failed` na hora, sem retentar | `transaction` reversal (`reverses_transaction_id` → payout): D Trânsito / C Cliente, criada na **mesma chamada** do reconcile ("na hora"); a payout original continua `pending` |
| `timeout` | `timeout` nas 3 tentativas | `pending` com backoff crescente após a 1ª e a 2ª; na 3ª sem resposta `→ failed` | idem `refuse`: a reversal devolve o dinheiro ao lojista |
| `flaky` | `timeout`, `timeout`, `confirmed` | `pending` após as 2 primeiras; `→ settled` na 3ª | como `confirm` na 3ª; nenhuma reversal. Prova que retry + backoff funcionam sem perder o payout |

Ver RFC v7.2 §2, passos 6-7 e "Caminhos alternativos" (mock sem resposta, recusa definitiva). Com `as_of` (ver `rotas.md`), os testes avançam o backoff entre as chamadas de reconcile sem esperar.

### Limites aceitos

- Estado em memória: reiniciar o mock zera os `transfer_id` e o contador do `flaky`.
- O risco "pagou, mas a resposta se perdeu" não existe aqui (RFC §2, perguntas de estresse): o mock nunca confirma e some.

## Domínio `bureau` (planejado)

Verificação de empresa (birô). Hoje é o `MockBureauConnector` dentro do Banco; migrará para cá numa fatia própria, com rotas sob `/bureau`. Contrato a ser escrito nessa fatia.
