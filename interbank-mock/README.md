# interbank-mock

Simulated interbank transfer provider. It stands in for the external system that moves a payout out of the institution, so the `transferencias` service can exercise confirmation, refusal, timeouts and retries without touching a real bank. No authentication (it is an external system). All state is in memory: restarting the container resets everything.

## Running

```bash
docker compose up -d interbank-mock
curl -i http://localhost:8003/health_check
```

| Env | Default | Meaning |
|---|---|---|
| `INTERBANK_MOCK_PORT` | `8003` | host port (the container always listens on 8003) |
| `MOCK_TIMEOUT_SECONDS` | `30` | how long a `timeout` response stalls, set well above the client timeout |

`transferencias-api` reaches it at `INTERBANK_API_URL=http://interbank-mock:8003`.

## Contract

`GET /health_check` returns `204`.

`POST /transfers`

```json
{"payout_key": "<uuid>", "amount_minor": 10000, "purpose": "payout", "destination": {"scenario": "confirm"}}
```

`destination` is a free object; only `destination.scenario` is interpreted.

| `destination.scenario` | Response |
|---|---|
| absent or `confirm` | `200 {"transfer_id": "<uuid v4>", "status": "confirmed"}` |
| `refuse` | `422 {"status": "refused", "reason": "destination_refused"}` (definitive) |
| `timeout` | stalls for `MOCK_TIMEOUT_SECONDS`, so the client times out |
| `flaky` | per `payout_key`: calls 1 and 2 behave as `timeout`, call 3 onwards confirms |
| anything else | `400` `RNV000001` |

An invalid body (missing field, `amount_minor` not a positive integer, `payout_key` not a UUID, extra fields, malformed JSON) returns `400` with `{title, description, translation, code}` and `code` `RNV000001`.

Idempotent by `payout_key`: repeated confirmations return the same `transfer_id`. Refusals and stalls are not remembered; `flaky` keeps a call counter per `payout_key`.

Every call is logged with `payout_key`, scenario and result.

## Tests

Black-box over HTTP; the mock must be up.

```bash
pip install -r interbank-mock/requirements-dev.txt
cd interbank-mock
python -m pytest tests/
```

`INTERBANK_MOCK_URL` overrides the target (default `http://localhost:8003`).
