"""Fila simples em memória para o MVP local/deploy de instância única."""
from __future__ import annotations

import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone

from app.agents.aquasmart_agent import AquaSmartAgent

_LOCK = threading.Lock()
_JOBS: dict[str, dict] = {}


def _now():
    return datetime.now(timezone.utc).isoformat()


def create_job(payload: dict) -> dict:
    job_id = uuid.uuid4().hex
    job = {
        "id": job_id,
        "status": "queued",
        "stage": "queued",
        "progress": 0,
        "message": "Análise adicionada à fila.",
        "created_at": _now(),
        "updated_at": _now(),
        "request": payload,
        "result": None,
        "error": None,
    }
    with _LOCK:
        _JOBS[job_id] = job
    return deepcopy(job)


def get_job(job_id: str) -> dict | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        return deepcopy(job) if job else None


def _update(job_id: str, **changes):
    with _LOCK:
        if job_id in _JOBS:
            _JOBS[job_id].update(changes)
            _JOBS[job_id]["updated_at"] = _now()


def run_job(job_id: str):
    job = get_job(job_id)
    if not job:
        return
    _update(job_id, status="running", message="Iniciando análise.")
    agent = AquaSmartAgent()

    def progress(stage: str, message: str, pct: int):
        _update(job_id, status="running", stage=stage, message=message, progress=pct)

    try:
        result = agent.analyze(job["request"], progress=progress)
        _update(job_id, status="completed", stage="done", progress=100, message="Análise concluída.", result=result)
    except Exception as exc:
        _update(job_id, status="failed", stage="error", message="A análise falhou.", error=f"{type(exc).__name__}: {exc}")
