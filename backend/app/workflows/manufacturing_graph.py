"""Manufacturing issue workflow orchestration."""

from __future__ import annotations

import uuid
from typing import Any, Optional, TypedDict

from app.agents.investigator_agent import investigator_node
from app.agents.scanner_agent import scanner_node
from app.agents.technician_agent import technician_node


class ManufacturingIssueState(TypedDict, total=False):
    run_id: str
    problem_statement: str
    plant_id: str
    line_id: str
    timeframe_start: str
    timeframe_end: str
    raw_sensor_data: list[dict[str, Any]]
    scanner_result: Optional[dict[str, Any]]
    retrieved_context: Optional[list[dict[str, Any]]]
    investigator_result: Optional[dict[str, Any]]
    technician_result: Optional[dict[str, Any]]
    approval_status: str
    final_report_path: Optional[str]
    has_anomaly: bool


RUN_STORE: dict[str, ManufacturingIssueState] = {}


async def _scanner_checkpoint_node(state: dict[str, Any]) -> dict[str, Any]:
    result = await scanner_node(state)
    RUN_STORE[result["run_id"]] = result
    return result


async def _investigator_checkpoint_node(state: dict[str, Any]) -> dict[str, Any]:
    result = await investigator_node(state)
    RUN_STORE[result["run_id"]] = result
    return result


async def _technician_checkpoint_node(state: dict[str, Any]) -> dict[str, Any]:
    result = await technician_node(state)
    RUN_STORE[result["run_id"]] = result
    return result


def route_after_scanner(state: dict[str, Any]) -> str:
    return "investigator" if state.get("has_anomaly") else "END"


def initial_state(payload: dict[str, Any]) -> ManufacturingIssueState:
    return {
        "run_id": payload.get("run_id") or str(uuid.uuid4()),
        "problem_statement": payload.get("problem_statement", ""),
        "plant_id": payload.get("plant_id", "PLANT-01"),
        "line_id": payload.get("line_id", "LINE-B"),
        "timeframe_start": payload.get("timeframe_start", ""),
        "timeframe_end": payload.get("timeframe_end", ""),
        "raw_sensor_data": payload.get("raw_sensor_data", []),
        "scanner_result": None,
        "retrieved_context": None,
        "investigator_result": None,
        "technician_result": None,
        "approval_status": "not_required",
        "final_report_path": None,
        "has_anomaly": False,
    }


class SequentialManufacturingGraph:
    """Dependency-light graph with the same node order as the LangGraph plan."""

    async def ainvoke(self, state: ManufacturingIssueState, config: dict[str, Any] | None = None):
        del config
        current = await scanner_node(state)
        RUN_STORE[current["run_id"]] = current

        if not current.get("has_anomaly"):
            return current

        current = await investigator_node(current)
        RUN_STORE[current["run_id"]] = current
        current = await technician_node(current)
        RUN_STORE[current["run_id"]] = current
        return current


_graph: Any | None = None


async def build_graph() -> Any:
    """Build LangGraph when available; otherwise use the local sequential graph."""
    try:
        import os

        from langgraph.graph import END, StateGraph

        graph = StateGraph(dict)
        graph.add_node("scanner", _scanner_checkpoint_node)
        graph.add_node("investigator", _investigator_checkpoint_node)
        graph.add_node("technician", _technician_checkpoint_node)
        graph.set_entry_point("scanner")
        graph.add_conditional_edges(
            "scanner",
            lambda state: "investigator" if state.get("has_anomaly") else END,
            {"investigator": "investigator", END: END},
        )
        graph.add_edge("investigator", "technician")
        graph.add_edge("technician", END)

        database_url = os.getenv("DATABASE_URL")
        if database_url:
            try:
                from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

                checkpointer = AsyncPostgresSaver.from_conn_string(database_url)
                await checkpointer.setup()
                return graph.compile(checkpointer=checkpointer)
            except Exception:
                pass

        return graph.compile()
    except Exception:
        return SequentialManufacturingGraph()


async def get_graph() -> Any:
    global _graph
    if _graph is None:
        _graph = await build_graph()
    return _graph


async def run_pipeline(run_id: str, state: ManufacturingIssueState) -> ManufacturingIssueState:
    graph = await get_graph()
    state["run_id"] = run_id
    config = {"configurable": {"thread_id": run_id}}
    result = await graph.ainvoke(state, config=config)
    RUN_STORE[run_id] = result
    return result


def update_approval(run_id: str, decision: str) -> ManufacturingIssueState:
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be approved or rejected")
    if run_id not in RUN_STORE:
        raise KeyError(run_id)
    RUN_STORE[run_id]["approval_status"] = decision
    return RUN_STORE[run_id]
