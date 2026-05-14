"""Database access with asyncpg when configured and an in-memory fallback for demos."""

from __future__ import annotations

import json
import asyncio
from typing import Any

from app.config import settings


_pool: Any | None = None
_memory_issues: dict[str, dict[str, Any]] = {}
_memory_audit: list[dict[str, Any]] = []


async def init_pool() -> None:
    global _pool
    if _pool is not None or not settings.database_url:
        return
    import asyncpg

    last_error: Exception | None = None
    for _ in range(12):
        try:
            _pool = await asyncpg.create_pool(settings.database_url)
            return
        except OSError as exc:
            last_error = exc
            await asyncio.sleep(1)
    if last_error:
        raise last_error


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def save_run(issue_id: str, result: dict[str, Any]) -> None:
    scanner = result.get("scanner_result") or {}
    investigator = result.get("investigator_result")
    technician = result.get("technician_result")
    status = result.get("status", "RUNNING")
    approval_status = result.get("approval_status", "pending")

    if _pool is None:
        _memory_issues[issue_id] = {"issue_id": issue_id, "status": status, **result}
        _memory_audit.append({"issue_id": issue_id, "event_type": "pipeline_saved", "payload": result})
        return

    async with _pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO production_issues
                  (issue_id, plant_id, line_id, problem_statement, severity, status, approval_status)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (issue_id) DO UPDATE
                SET severity = EXCLUDED.severity,
                    status = EXCLUDED.status,
                    approval_status = EXCLUDED.approval_status
                """,
                issue_id,
                result.get("plant_id", "PLANT-01"),
                result.get("line_id", scanner.get("line_id", "LINE-B")),
                result.get("problem_statement", ""),
                scanner.get("severity"),
                status,
                approval_status,
            )
            await conn.execute(
                """
                INSERT INTO pipeline_runs
                  (issue_id, scanner_output, investigator_output, technician_output, retrieved_context, pdf_path)
                VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, $5, $6)
                """,
                issue_id,
                json.dumps(scanner),
                json.dumps(investigator),
                json.dumps(technician),
                json.dumps(result.get("retrieved_context")),
                result.get("final_report_path"),
            )
            await conn.execute(
                """
                INSERT INTO audit_log (issue_id, event_type, actor, payload)
                VALUES ($1, 'pipeline_saved', 'system', $2::jsonb)
                """,
                issue_id,
                json.dumps(result),
            )


async def get_run(issue_id: str) -> dict[str, Any] | None:
    if _pool is None:
        return _memory_issues.get(issue_id)

    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT i.*, r.scanner_output, r.investigator_output, r.technician_output,
                   r.retrieved_context, r.pdf_path
            FROM production_issues i
            LEFT JOIN LATERAL (
              SELECT * FROM pipeline_runs pr
              WHERE pr.issue_id = i.issue_id
              ORDER BY pr.created_at DESC
              LIMIT 1
            ) r ON true
            WHERE i.issue_id = $1
            """,
            issue_id,
        )
    return dict(row) if row else None


async def update_approval(issue_id: str, decision: str, approver: str, notes: str = "") -> dict[str, Any]:
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be approved or rejected")

    payload = {"decision": decision, "approver": approver, "notes": notes}
    if _pool is None:
        if issue_id not in _memory_issues:
            raise KeyError(issue_id)
        _memory_issues[issue_id]["approval_status"] = decision
        _memory_issues[issue_id]["approver"] = approver
        _memory_issues[issue_id]["approval_notes"] = notes
        _memory_audit.append({"issue_id": issue_id, "event_type": "approval", "payload": payload})
        return _memory_issues[issue_id]

    async with _pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                UPDATE production_issues
                SET approval_status = $2, approver = $3, approval_notes = $4
                WHERE issue_id = $1
                RETURNING *
                """,
                issue_id,
                decision,
                approver,
                notes,
            )
            if row is None:
                raise KeyError(issue_id)
            await conn.execute(
                """
                INSERT INTO audit_log (issue_id, event_type, actor, payload)
                VALUES ($1, 'approval', $2, $3::jsonb)
                """,
                issue_id,
                approver,
                json.dumps(payload),
            )
    return dict(row)
