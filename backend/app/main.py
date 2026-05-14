"""FastAPI entrypoint for sensor streaming and manufacturing agent workflows."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from app.schemas.issue_schema import AnalyzeRequest, ApprovalRequest
from app.services.database_service import (
    close_pool,
    get_run,
    init_pool,
    save_run,
    update_approval as update_db_approval,
)
from app.services.simulation_service import generate_scenario_batch
from app.workflows.manufacturing_graph import (
    RUN_STORE,
    initial_state,
    run_pipeline,
    update_approval as update_workflow_approval,
)

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="Production Issue Resolution Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _new_issue_id() -> str:
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"ISSUE-{date}-{uuid.uuid4().hex[:6].upper()}"


async def _run_pipeline_task(issue_id: str, request: AnalyzeRequest) -> None:
    raw_sensor_data = request.raw_sensor_data
    if not raw_sensor_data and request.scenario:
        raw_sensor_data = generate_scenario_batch(request.scenario)

    state = initial_state(
        {
            "run_id": issue_id,
            "problem_statement": request.problem_statement,
            "plant_id": request.plant_id,
            "line_id": request.line_id,
            "timeframe_start": request.timeframe_start,
            "timeframe_end": request.timeframe_end,
            "raw_sensor_data": raw_sensor_data,
        }
    )
    RUN_STORE[issue_id] = {**state, "status": "RUNNING"}
    try:
        result = await run_pipeline(issue_id, state)
        result["status"] = "DONE"
        RUN_STORE[issue_id] = result
        await save_run(issue_id, result)
    except Exception as exc:
        RUN_STORE[issue_id] = {**state, "status": "FAILED", "error": str(exc)}


@app.post("/api/pipeline/run")
async def run_manufacturing_pipeline(payload: dict) -> dict:
    state = initial_state(payload)
    result = await run_pipeline(state["run_id"], state)
    result["status"] = "DONE"
    await save_run(state["run_id"], result)
    return result


@app.post("/api/issues/analyze")
async def analyze_issue(request: AnalyzeRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    issue_id = _new_issue_id()
    RUN_STORE[issue_id] = {
        **initial_state({"run_id": issue_id, **request.model_dump()}),
        "status": "RUNNING",
    }
    background_tasks.add_task(_run_pipeline_task, issue_id, request)
    return {"issue_id": issue_id, "status": "RUNNING"}


@app.get("/api/issues/{issue_id}")
async def get_issue(issue_id: str) -> dict:
    run = RUN_STORE.get(issue_id) or await get_run(issue_id)
    if run is None:
        raise HTTPException(status_code=404, detail="issue_id not found")
    return run


@app.post("/api/issues/{issue_id}/approve")
async def approve_issue(issue_id: str, request: ApprovalRequest) -> dict:
    try:
        state = update_workflow_approval(issue_id, request.decision)
        try:
            await update_db_approval(issue_id, request.decision, request.approver, request.notes)
        except KeyError:
            pass
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="run_id not found") from exc
    return {"issue_id": issue_id, "approval_status": state["approval_status"]}


@app.get("/api/reports/{issue_id}/pdf")
async def download_report(issue_id: str) -> FileResponse:
    run = RUN_STORE.get(issue_id) or await get_run(issue_id)
    if run is None:
        raise HTTPException(status_code=404, detail="issue_id not found")
    path = run.get("final_report_path") or run.get("pdf_path")
    if not path:
        technician = run.get("technician_result") or run.get("technician_output") or {}
        path = technician.get("pdf_path")
    if not path:
        raise HTTPException(status_code=404, detail="PDF not generated")
    return FileResponse(path, media_type="application/pdf", filename=f"{issue_id}.pdf")


@app.post("/api/simulation/start")
def simulation_start(payload: dict | None = None) -> dict[str, str]:
    scenario = (payload or {}).get("scenario", "live")
    return {"sse_url": f"/stream/sensor?scenario={scenario}"}


@app.get("/stream/sensor")
async def stream_sensor(scenario: str = "live") -> StreamingResponse:
    async def events():
        if scenario == "pressure_drop":
            yield f"data: {json.dumps(generate_scenario_batch(scenario))}\n\n"
            return
        while True:
            try:
                yield f"data: {json.dumps(generate_scenario_batch(scenario))}\n\n"
            except Exception:
                log.exception("sse.batch_error scenario=%s", scenario)
                yield 'data: {"error": "batch generation failed"}\n\n'
            await asyncio.sleep(1.5)

    return StreamingResponse(events(), media_type="text/event-stream")
