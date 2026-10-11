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
| 2 | POST | `/accounts/{account_key}/close` | cliente | Encerra; `409 RNV001009` se a conta não está `active`; `409 RNV001012` se tem saldo. |

### Ledger

| Prioridade | Método | Rota | Acesso | Justificativa |
|---|---|---|---|---|
| 1 | POST | `/ledger/transactions` | serviço | Lançamento idempotente de partida dobrada. Valida fechamento e dedupe. |

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
| 2 | POST | `/payments/{payment_key}/refund` | cliente | Reembolso; `409 RNV001026` fora da janela, `409 RNV001003` já estornado. Sem Idempotency-Key (estado `held`→`refunded` guarda). |
| 3 | GET | `/payments` | cliente | Lista paginada do lojista. |

### Payout (saída de dinheiro)

| Prioridade | Método | Rota | Acesso | Justificativa |
|---|---|---|---|---|
| 1 | POST | `/payouts` | cliente | Saída externa (saque/boleto/transferência); `destination` imutável; debita a conta. |
| 2 | GET | `/payouts/{payout_key}` | cliente | Consulta saque; IDOR → `404 RNV001032`. |

### Internal (jobs)

| Prioridade | Método | Rota | Acesso | Justificativa |
|---|---|---|---|---|
| 1 | POST | `/internal/settlements` | serviço | Job de liberação: in_transit → cliente ao fim da janela. |
| 2 | POST | `/internal/payouts/reconcile` | serviço | Job de reconciliação do payout (confirma/falha; reversal ao falhar). |

**`as_of` nos jobs.** Os dois endpoints aceitam corpo opcional para injetar o "agora", de modo que testes e operação não precisem esperar a janela (24h/72h/720h) nem o backoff:

```json
{"as_of": "2026-10-12T12:00:00-03:00"}
```

- **Ausente** (corpo vazio ou sem a chave) = relógio do servidor.
- **Formato:** ISO 8601 **com fuso** (offset ou `Z`). Sem fuso ou não-ISO → `400 RNV000001` (JSON Schema na porta, antes de qualquer consulta).
- **Acesso:** só existe em `/internal/*` (`INTERNAL-TOKEN`; sem ele, `403 RNV000002`). **Nunca** é aceito em rota de cliente: serve a testes e operação, não ao produto.
- **`POST /internal/settlements`:** libera os `payment` em `held` com `release_at <= as_of`. A chave determinística (`settlement:<payment_key>`) e o `FOR UPDATE` na linha do `payment` continuam valendo; rodar de novo com o mesmo `as_of` é no-op.
- **`POST /internal/payouts/reconcile`:** `as_of` é o "agora" que decide se a próxima tentativa/backoff do payout já venceu (`last_attempt_at` + espera) e o `now` gravado ao registrar a `payout_attempt`.

O mock interbancário que o reconcile chama (`POST /interbank/transfers` no `external-mocks`) está em `mocks-externos.md`.

### Admin

| Prioridade | Método | Rota | Acesso |
|---|---|---|---|
| 3 | GET | `/admin/payments` | admin |

---

## Sugestões incorporadas (refino da v7)

- `POST /accounts/{account_key}/close` só encerra com **saldo zero** (`409 RNV001012` caso contrário).
- `GET /admin/internal-accounts` para auditar as três contas internas (reserves / in_transit / revenue).
- `GET /payouts/{payout_key}` para o lojista acompanhar o saque.
- Novos códigos: `RNV001030` (empresa sem conta aberta), `RNV001031` (conta não active, só escrita),
  `RNV001032` (saque inexistente ou de outro lojista).
- `as_of` opcional no corpo de `POST /internal/settlements` e `POST /internal/payouts/reconcile`: refino
  em cima da RFC v7.2, que não menciona `as_of` (ela fala só em "o relógio" e "quando `release_at` vence").
  Sem o campo, nada muda; existe para testar sem esperar a janela. Só com `INTERNAL-TOKEN`.
