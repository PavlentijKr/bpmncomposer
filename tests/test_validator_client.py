import asyncio

import pytest

import app.validator_client as validator_client
import httpx_stub


def test_validator_accepts_bpmnlint_response(monkeypatch):
    monkeypatch.setattr(validator_client, "httpx", httpx_stub)

    class DummyAsyncClient(httpx_stub.AsyncClient):
        async def post(self, url, headers=None, content=None, **kwargs):
            return httpx_stub.Response(
                status_code=200,
                json={
                    "issues": [
                        {
                            "id": "Task_1",
                            "rule": "bpmnlint:label-required",
                            "message": "Task must have a label",
                            "category": "error",
                        },
                        {
                            "id": "Task_2",
                            "rule": "bpmnlint:no-manual-task",
                            "message": "Manual tasks are discouraged",
                            "category": "warn",
                        },
                    ]
                },
            )

    monkeypatch.setattr(httpx_stub, "AsyncClient", DummyAsyncClient)

    client = validator_client.ValidatorClient("http://validator")
    report = asyncio.run(client.validate("<bpmn></bpmn>"))

    assert len(report.errors) == 1
    assert report.errors[0].rule == "bpmnlint:label-required"
    assert len(report.warnings) == 1
    assert report.warnings[0].rule == "bpmnlint:no-manual-task"


def test_validator_rejects_unknown_format(monkeypatch):
    monkeypatch.setattr(validator_client, "httpx", httpx_stub)

    class DummyAsyncClient(httpx_stub.AsyncClient):
        async def post(self, url, headers=None, content=None, **kwargs):
            return httpx_stub.Response(status_code=200, json={"unexpected": "value"})

    monkeypatch.setattr(httpx_stub, "AsyncClient", DummyAsyncClient)

    client = validator_client.ValidatorClient("http://validator")

    with pytest.raises(validator_client.ValidatorError):
        asyncio.run(client.validate("<bpmn></bpmn>"))
