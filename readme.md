# BPMN Composer API

FastAPI service that generates BPMN 2.0 XML diagrams from text descriptions using GigaChat and validates them through an external validator service.

## Configuration
Environment variables:

- `GIGACHAT_API_URL` – GigaChat API base endpoint (e.g. `https://gigachat.devices.sberbank.ru/api/v1`).
- `GIGACHAT_AUTH_URL` – OAuth endpoint for issuing access tokens (e.g. `https://ngw.devices.sberbank.ru:9443/api/v2/oauth`).
- `GIGACHAT_CREDENTIALS` – authorization credentials used to request tokens (same value as the Postman `credentials` variable, sent as Bearer).
- `GIGACHAT_SCOPE` – token scope (defaults to `GIGACHAT_API_CORP`).
- `GIGACHAT_MODEL` – chat model identifier (defaults to `GigaChat:latest`).
- `GIGACHAT_TOKEN` – optional pre-fetched access token (used if provided instead of requesting a new one).
- `VALIDATOR_URL` – validator endpoint (e.g. `http://validator:9000/validate`).
- `MAX_ATTEMPTS_DEFAULT` – default retry count.
- `MAX_ATTEMPTS_HARD_LIMIT` – hard limit for attempts.
- `MAX_TEXT_LEN` – maximum allowed source text length.
- `LLM_TIMEOUT_SEC` – timeout for LLM calls.
- `VALIDATOR_TIMEOUT_SEC` – timeout for validator calls.
- `LOG_LEVEL` – logging level (defaults to `INFO`).

## Running

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API (uvicorn example):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Tests

Run the test suite:

```bash
pytest
```
