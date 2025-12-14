import asyncio
import json
import pathlib
import sys

import pytest
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.main import generate_bpmn
from app.models import GenerateRequest, ValidationReport
from app.service import GenerationService
from app.validator_client import ValidatorClient


@pytest.fixture(autouse=True)
def reset_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def apply_env(monkeypatch):
    monkeypatch.setenv("GIGACHAT_API_URL", "http://gigachat")
    monkeypatch.setenv("GIGACHAT_TOKEN", "token")
    monkeypatch.setenv("VALIDATOR_URL", "http://validator/validate")
    monkeypatch.setenv("MAX_ATTEMPTS_DEFAULT", "3")
    monkeypatch.setenv("MAX_ATTEMPTS_HARD_LIMIT", "5")


def call_endpoint(payload):
    try:
        request = GenerateRequest(**payload)
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    try:
        response = asyncio.run(generate_bpmn(request=request, settings=get_settings()))
        if hasattr(response, "body"):
            response.json = lambda: json.loads(response.body.decode())  # type: ignore[attr-defined]
        return response
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def sample_bpmn(name: str) -> str:
    return f"""
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Definitions_1">
  <bpmn:process id="Process_1" name="{name}" isExecutable="false">
    <bpmn:startEvent id="StartEvent_1" name="Start" />
    <bpmn:task id="Task_1" name="Do" />
    <bpmn:endEvent id="EndEvent_1" name="End" />
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="EndEvent_1" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
      <bpmndi:BPMNShape id="Shape_Start" bpmnElement="StartEvent_1">
        <dc:Bounds x="100" y="100" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Shape_Task" bpmnElement="Task_1">
        <dc:Bounds x="170" y="90" width="100" height="60" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Shape_End" bpmnElement="EndEvent_1">
        <dc:Bounds x="310" y="100" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Edge_1" bpmnElement="Flow_1">
        <di:waypoint xmlns:di="http://www.omg.org/spec/DD/20100524/DI" x="136" y="118" />
        <di:waypoint xmlns:di="http://www.omg.org/spec/DD/20100524/DI" x="170" y="120" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Edge_2" bpmnElement="Flow_2">
        <di:waypoint xmlns:di="http://www.omg.org/spec/DD/20100524/DI" x="270" y="120" />
        <di:waypoint xmlns:di="http://www.omg.org/spec/DD/20100524/DI" x="310" y="118" />
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
"""


def test_generate_success(monkeypatch):
    apply_env(monkeypatch)

    async def llm_ok(self, prompt, temperature, repair):
        return sample_bpmn("Success")

    monkeypatch.setattr(GenerationService, "_call_llm", llm_ok)
    async def validate_ok(self, xml):
        return ValidationReport(errors=[], warnings=[])

    monkeypatch.setattr(ValidatorClient, "validate", validate_ok)

    response = call_endpoint({"text": "Test process", "return_debug": True})
    assert response.status_code == 200
    body = response.json()
    assert body["validated"] is True
    assert body["attempts_used"] == 1
    assert "bpmn:definitions" in body["bpmn_xml"]
    assert body["debug"]["attempts"][0]["validation_report"]["errors"] == []


def test_generate_repair(monkeypatch):
    apply_env(monkeypatch)

    calls = {"count": 0}

    async def fake_llm(self, prompt, temperature, repair):
        calls["count"] += 1
        return sample_bpmn("Fixed" if repair else "Bad")

    reports = [
        ValidationReport(errors=[{"message": "issue"}], warnings=[]),
        ValidationReport(errors=[], warnings=[]),
    ]

    async def fake_validate(self, xml):
        return reports.pop(0)

    monkeypatch.setattr(GenerationService, "_call_llm", fake_llm)
    monkeypatch.setattr(ValidatorClient, "validate", fake_validate)

    response = call_endpoint({"text": "Needs repair", "return_debug": True, "max_attempts": 2})
    assert response.status_code == 200
    data = response.json()
    assert data["validated"] is True
    assert data["attempts_used"] == 2
    assert data["debug"]["attempts"][0]["validation_report"]["errors"]


def test_generate_exhausted(monkeypatch):
    apply_env(monkeypatch)

    async def llm_bad(self, prompt, temperature, repair):
        return sample_bpmn("Still Bad")

    monkeypatch.setattr(GenerationService, "_call_llm", llm_bad)

    async def always_fail(self, xml):
        return ValidationReport(errors=[{"message": "issue"}], warnings=[])

    monkeypatch.setattr(ValidatorClient, "validate", always_fail)

    response = call_endpoint({"text": "Always bad", "max_attempts": 2})
    assert response.status_code == 422
    body = response.json()
    assert body["validated"] is False
    assert body["attempts_used"] == 2
    assert body["last_validation_report"]["errors"]


def test_reject_empty_text(monkeypatch):
    apply_env(monkeypatch)
    response = call_endpoint({"text": "   "})
    assert response.status_code == 422


def test_reject_large_text(monkeypatch):
    apply_env(monkeypatch)
    monkeypatch.setenv("MAX_TEXT_LEN", "5")
    response = call_endpoint({"text": "123456"})
    assert response.status_code == 400
