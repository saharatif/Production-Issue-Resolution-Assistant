import time
import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.investigator_schema import InvestigatorOutput
from app.schemas.scanner_schema import ScannerOutput
from app.schemas.technician_schema import TechnicianOutput
from app.services.pinecone_service import retrieve_similar
from app.services.simulation_service import demo_scenario_line_b_pressure_drop


class Module3ApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_schemas_validate_agent_json(self):
        scanner = ScannerOutput(
            anomaly_detected=True,
            plant_id="PLANT-01",
            line_id="LINE-B",
            machine_id="PRESS-VALVE-23",
            anomaly_type=["LOW_PRESSURE"],
            severity="HIGH",
            details=["pressure low"],
            recommended_next_agent="Investigator Agent",
        )
        investigator = InvestigatorOutput(
            verdict="Stabilize",
            root_cause_hypotheses=[
                {
                    "hypothesis": "Pressure valve actuator drift.",
                    "confidence": 0.82,
                    "confidence_breakdown": {
                        "historical_similarity": 0.35,
                        "threshold_violation_strength": 0.25,
                        "maintenance_history_match": 0.25,
                        "data_completeness": 0.15,
                    },
                    "supporting_evidence": ["INC-2026-0312-LINE-B-004"],
                }
            ],
            recommendations={"stabilize": [], "investigate": [], "prevent_recurrence": []},
            compliance_reference=["SOP-LINE-B-PRESSURE-001"],
        )
        technician = TechnicianOutput(
            shift_handoff_note={
                "title": "Shift Handoff",
                "summary": "Low pressure.",
                "current_status": "Controlled operation.",
                "actions_completed": [],
                "open_actions": [],
            },
            maintenance_request={
                "priority": "HIGH",
                "asset": "PRESS-VALVE-23",
                "line_id": "LINE-B",
                "request": "Inspect valve.",
                "reason": "Low pressure.",
            },
            corrective_action_plan={
                "problem": "Low pressure.",
                "containment": "Reduce speed.",
                "root_cause_analysis": "Valve drift.",
                "corrective_action": "Recalibrate.",
                "preventive_action": "PM update.",
            },
            supplier_questions=[],
        )

        self.assertTrue(scanner.anomaly_detected)
        self.assertEqual(investigator.verdict, "Stabilize")
        self.assertEqual(technician.maintenance_request.priority, "HIGH")

    def test_analyze_poll_approve_and_pdf(self):
        response = self.client.post(
            "/api/issues/analyze",
            json={
                "problem_statement": "Pressure drop on Line B",
                "plant_id": "PLANT-01",
                "line_id": "LINE-B",
                "raw_sensor_data": demo_scenario_line_b_pressure_drop(),
            },
        )
        self.assertEqual(response.status_code, 200)
        issue_id = response.json()["issue_id"]

        run = None
        for _ in range(10):
            poll = self.client.get(f"/api/issues/{issue_id}")
            self.assertEqual(poll.status_code, 200)
            run = poll.json()
            if run.get("status") == "DONE":
                break
            time.sleep(0.05)

        self.assertIsNotNone(run)
        self.assertEqual(run["status"], "DONE")
        self.assertEqual(run["approval_status"], "pending")

        approval = self.client.post(
            f"/api/issues/{issue_id}/approve",
            json={"decision": "approved", "approver": "Test Manager", "notes": "Looks good."},
        )
        self.assertEqual(approval.status_code, 200)
        self.assertEqual(approval.json()["approval_status"], "approved")

        pdf = self.client.get(f"/api/reports/{issue_id}/pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.headers["content-type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_simulation_start_returns_sse_url(self):
        response = self.client.post("/api/simulation/start", json={"scenario": "pressure_drop"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sse_url"], "/stream/sensor?scenario=pressure_drop")

    def test_pinecone_service_returns_empty_without_credentials(self):
        self.assertEqual(retrieve_similar("pressure", filter_meta={"line_id": {"$eq": "LINE-B"}}), [])


if __name__ == "__main__":
    unittest.main()
