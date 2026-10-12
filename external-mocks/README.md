# external-mocks

Simulador dos sistemas externos dos quais o projeto depende. Um único container, uma rota raiz por domínio externo, para os serviços (`transferencias`, `banco`) exercitarem confirmação, recusa, timeout e retry sem tocar em sistemas reais. Sem autenticação (são sistemas externos). Todo o estado fica em memória: reiniciar o container zera tudo.

## Como subir

```bash
docker compose up -d external-mocks
curl -i http://localhost:8003/health_check
```

| Variável | Padrão | Significado |
|---|---|---|
| `EXTERNAL_MOCKS_PORT` | `8003` | porta no host (o container sempre escuta na 8003) |
| `MOCK_TIMEOUT_SECONDS` | `30` | quanto tempo o cenário `timeout` segura a resposta; deve ficar bem acima do timeout do cliente |

O `transferencias-api` acessa o mock em `INTERBANK_API_URL=http://external-mocks:8003` (timeout do cliente em `INTERBANK_TIMEOUT_SECONDS`, padrão 5).

## Domínios

| Domínio | Prefixo | Situação |
|---|---|---|
| Interbancário (saída de payout) | `/interbank` | disponível |
| Birô (verificação de empresa) | `/bureau` | planejado |

`GET /health_check` fica na raiz e responde `204`; `GET /` devolve `{"service": "external-mocks"}`.

Para acrescentar um domínio, crie `resources/<dominio>_*.py`, `controllers/<dominio>_*_controller.py`, `repositories/<dominio>_*_repository.py` e o schema em `schemas/`, e registre a rota em `src/app.py` com o prefixo do domínio. O interbancário não é tocado.

## Interbancário: `POST /interbank/transfers`

```json
{"payout_key": "<uuid>", "amount_minor": 10000, "purpose": "payout", "destination": {"scenario": "confirm"}}
```

`destination` é um objeto livre; só `destination.scenario` é interpretado.

| `destination.scenario` | Resposta |
|---|---|
| ausente ou `confirm` | `200 {"transfer_id": "<uuid v4>", "status": "confirmed"}` |
| `refuse` | `422 {"status": "refused", "reason": "destination_refused"}` (definitiva) |
| `timeout` | segura a resposta por `MOCK_TIMEOUT_SECONDS`, e o cliente estoura o timeout |
| `flaky` | por `payout_key`: as chamadas 1 e 2 se comportam como `timeout`, da 3ª em diante confirma |
| qualquer outro valor | `400` `RNV000009` |

Corpo inválido devolve `400` com `{title, description, translation, code}`, um código por tipo: `RNV000007` campo faltando, `RNV000008` campo extra, `RNV000009` tipo ou formato errado (`payout_key` que não seja UUID, `amount_minor` que não seja inteiro), `RNV000010` fora do limite (`amount_minor` <= 0, `purpose` vazio), `RNV000001` corpo que não é objeto JSON.

Idempotente por `payout_key`: confirmações repetidas devolvem o mesmo `transfer_id`. Recusas e travamentos não são lembrados; o `flaky` guarda um contador de chamadas por `payout_key`.

Toda chamada é logada com `payout_key`, cenário e resultado.

## Testes

Caixa-preta por HTTP; o mock precisa estar de pé.

```bash
pip install -r external-mocks/requirements-dev.txt
cd external-mocks
python -m pytest tests/
```

`EXTERNAL_MOCKS_URL` troca o alvo (padrão `http://localhost:8003`).
