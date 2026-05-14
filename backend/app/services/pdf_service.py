"""PDF generation for technician action plans."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings

REPORT_DIR = Path(settings.report_dir or os.getenv("REPORT_DIR", "backend/app/reports"))


def _write_minimal_pdf(path: Path, title: str, lines: list[str]) -> None:
    text = "\\n".join([title, "", *lines])[:3000]
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 11 Tf 50 760 Td 14 TL ({escaped}) Tj ET"
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        f"5 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream endobj",
    ]
    body = "%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(body))
        body += obj + "\n"
    xref_start = len(body)
    body += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    body += "".join(f"{offset:010d} 00000 n \n" for offset in offsets[1:])
    body += f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n"
    path.write_bytes(body.encode("latin-1", errors="replace"))


def _flatten_list(items: list[Any]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- None"


def _fmt_shift_handoff(note: dict[str, Any]) -> str:
    if not note:
        return "No shift handoff note available."
    lines = [
        f"Title: {note.get('title', '')}",
        f"Summary: {note.get('summary', '')}",
        f"Current Status: {note.get('current_status', '')}",
        "",
        "Actions Completed:",
        _flatten_list(note.get("actions_completed", [])),
        "",
        "Open Actions:",
        _flatten_list(note.get("open_actions", [])),
    ]
    return "\n".join(lines)


def _fmt_maintenance_request(req: dict[str, Any]) -> str:
    if not req:
        return "No maintenance request available."
    return "\n".join([
        f"Priority:  {req.get('priority', '')}",
        f"Asset:     {req.get('asset', '')}",
        f"Line:      {req.get('line_id', '')}",
        f"Request:   {req.get('request', '')}",
        f"Reason:    {req.get('reason', '')}",
    ])


def _fmt_corrective_action_plan(cap: dict[str, Any]) -> str:
    if not cap:
        return "No corrective action plan available."
    return "\n".join([
        f"Problem:              {cap.get('problem', '')}",
        f"Containment:          {cap.get('containment', '')}",
        f"Root Cause Analysis:  {cap.get('root_cause_analysis', '')}",
        f"Corrective Action:    {cap.get('corrective_action', '')}",
        f"Preventive Action:    {cap.get('preventive_action', '')}",
    ])


def _fmt_recommendations(recs: dict[str, Any]) -> str:
    if not recs:
        return "No recommendations available."
    sections = []
    labels = {
        "stabilize": "Stabilize (Act Now)",
        "investigate": "Investigate (This Shift)",
        "prevent_recurrence": "Prevent Recurrence (Days / Weeks)",
    }
    for key, label in labels.items():
        items = recs.get(key, [])
        sections.append(f"{label}:\n{_flatten_list(items)}")
    return "\n\n".join(sections)


def _fallback_lines(
    run_id: str,
    scanner_result: dict[str, Any],
    investigator: dict[str, Any],
    technician: dict[str, Any],
) -> list[str]:
    return [
        f"Verdict: {investigator.get('verdict', 'Investigate')}",
        f"Detected anomalies: {', '.join(scanner_result.get('anomaly_type', []))}",
        f"Scanner details: {'; '.join(scanner_result.get('details', []))}",
        f"Recommendations: {_fmt_recommendations(investigator.get('recommendations', {}))}",
        f"Shift handoff: {_fmt_shift_handoff(technician.get('shift_handoff_note', {}))}",
        f"Maintenance request: {_fmt_maintenance_request(technician.get('maintenance_request', {}))}",
        f"Corrective action plan: {_fmt_corrective_action_plan(technician.get('corrective_action_plan', {}))}",
        f"Compliance references: {investigator.get('compliance_reference', [])}",
    ]


def generate_action_plan_pdf(
    run_id: str,
    scanner_result: dict[str, Any],
    investigator: dict[str, Any],
    technician: dict[str, Any],
) -> str:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"action_plan_{run_id[:12]}.pdf"
    title = f"Manufacturing Action Plan - {run_id}"
    lines = _fallback_lines(run_id, scanner_result, investigator, technician)

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=36, leftMargin=36)
        verdict = investigator.get("verdict", "Investigate")
        banner_color = {
            "Stabilize": colors.HexColor("#b91c1c"),
            "Investigate": colors.HexColor("#b45309"),
            "Prevent Recurrence": colors.HexColor("#0f766e"),
        }.get(verdict, colors.HexColor("#334155"))
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        story: list[Any] = [
            Paragraph(title, styles["Title"]),
            Paragraph(f"Issue ID: {run_id} | Generated: {generated_at}", styles["Normal"]),
            Paragraph("Generated by Manufacturing Issue Resolution System - Confidential", styles["Normal"]),
            Spacer(1, 12),
            Table(
                [[f"Verdict: {verdict}"]],
                colWidths=[500],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), banner_color),
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                        ("PADDING", (0, 0), (-1, -1), 8),
                    ]
                ),
            ),
            Spacer(1, 12),
        ]

        sections = [
            ("Detected Anomalies", _flatten_list(scanner_result.get("details", []))),
            (
                "Root Cause Hypotheses",
                _flatten_list(
                    [
                        f"{item.get('hypothesis')} ({round(item.get('confidence', 0) * 100)}%)"
                        for item in investigator.get("root_cause_hypotheses", [])
                    ]
                ),
            ),
            ("Recommendations", _fmt_recommendations(investigator.get("recommendations", {}))),
            ("Shift Handoff Note", _fmt_shift_handoff(technician.get("shift_handoff_note", {}))),
            ("Maintenance Request", _fmt_maintenance_request(technician.get("maintenance_request", {}))),
            ("Corrective Action Plan", _fmt_corrective_action_plan(technician.get("corrective_action_plan", {}))),
            ("Compliance References", _flatten_list(investigator.get("compliance_reference", []))),
        ]

        for heading, body in sections:
            story.extend(
                [
                    Paragraph(heading, styles["Heading2"]),
                    Paragraph(body.replace("\n", "<br/>"), styles["BodyText"]),
                    Spacer(1, 8),
                    HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1")),
                    Spacer(1, 8),
                ]
            )
        doc.build(story)
    except Exception:
        _write_minimal_pdf(path, title, lines)

    return str(path)
