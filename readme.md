# BPMN Composer API

FastAPI service that generates BPMN 2.0 XML diagrams from text descriptions using GigaChat and validates them through an external validator service.

## Configuration
Environment variables:

- `GIGACHAT_API_URL` – GigaChat API endpoint.
- `GIGACHAT_TOKEN` – token for GigaChat requests.
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
