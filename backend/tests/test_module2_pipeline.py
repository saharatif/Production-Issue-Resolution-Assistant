import asyncio
import unittest
from pathlib import Path

from app.agents.investigator_agent import CONFIDENCE_BREAKDOWN, _build_kb_context
from app.agents.scanner_agent import classify_batch
from app.services.llm_utils import safe_llm_call
from app.services.simulation_service import demo_scenario_line_b_pressure_drop, generate_batch
from app.workflows.manufacturing_graph import initial_state, run_pipeline, update_approval


class Module2PipelineTest(unittest.TestCase):
    def test_scanner_returns_no_anomaly_for_normal_batch(self):
        result = classify_batch(generate_batch(anomaly_probability=0))

        self.assertFalse(result["anomaly_detected"])
        self.assertEqual(result["severity"], "NONE")

    def test_scanner_classifies_pressure_drop(self):
        result = classify_batch(demo_scenario_line_b_pressure_drop())

        self.assertTrue(result["anomaly_detected"])
        self.assertIn("LOW_PRESSURE", result["anomaly_type"])
        self.assertEqual(result["line_id"], "LINE-B")

    def test_investigator_context_returns_line_b_pressure_documents(self):
        context = _build_kb_context([{"anomaly_type": ["LOW_PRESSURE"]}], "LINE-B")

        self.assertGreaterEqual(len(context), 1)
        self.assertTrue(any("PRESS-VALVE-23" in item["text"] for item in context))

    def test_confidence_breakdown_sums_to_one(self):
        self.assertLessEqual(sum(CONFIDENCE_BREAKDOWN.values()), 1.0)

    def test_pipeline_generates_pdf_and_pending_approval_for_anomaly(self):
        state = initial_state(
            {
                "run_id": "test-module2-pressure",
                "problem_statement": "Pressure drop on Line B",
                "plant_id": "PLANT-01",
                "line_id": "LINE-B",
                "raw_sensor_data": demo_scenario_line_b_pressure_drop(),
            }
        )

        result = asyncio.run(run_pipeline(state["run_id"], state))

        self.assertTrue(result["has_anomaly"])
        self.assertEqual(result["approval_status"], "pending")
        self.assertIn("shift_handoff_note", result["technician_result"])
        self.assertIn("maintenance_request", result["technician_result"])
        self.assertIn("corrective_action_plan", result["technician_result"])
        self.assertIn("supplier_questions", result["technician_result"])
        self.assertTrue(Path(result["final_report_path"]).exists())

    def test_pipeline_stops_after_scanner_for_clean_batch(self):
        state = initial_state(
            {
                "run_id": "test-module2-clean",
                "line_id": "LINE-A",
                "raw_sensor_data": generate_batch(anomaly_probability=0),
            }
        )

        result = asyncio.run(run_pipeline(state["run_id"], state))

        self.assertFalse(result["has_anomaly"])
        self.assertIsNone(result["investigator_result"])
        self.assertEqual(result["approval_status"], "not_required")

    def test_approval_update_changes_pending_status(self):
        state = initial_state(
            {
                "run_id": "test-module2-approval",
                "line_id": "LINE-B",
                "raw_sensor_data": demo_scenario_line_b_pressure_drop(),
            }
        )
        asyncio.run(run_pipeline(state["run_id"], state))

        updated = update_approval(state["run_id"], "approved")

        self.assertEqual(updated["approval_status"], "approved")

    def test_concurrent_runs_do_not_share_state(self):
        async def run_two():
            first = initial_state(
                {
                    "run_id": "test-module2-concurrent-a",
                    "line_id": "LINE-A",
                    "raw_sensor_data": generate_batch(anomaly_probability=0),
                }
            )
            second = initial_state(
                {
                    "run_id": "test-module2-concurrent-b",
                    "line_id": "LINE-B",
                    "raw_sensor_data": demo_scenario_line_b_pressure_drop(),
                }
            )
            return await asyncio.gather(
                run_pipeline(first["run_id"], first),
                run_pipeline(second["run_id"], second),
            )

        clean, anomalous = asyncio.run(run_two())

        self.assertEqual(clean["run_id"], "test-module2-concurrent-a")
        self.assertEqual(anomalous["run_id"], "test-module2-concurrent-b")
        self.assertFalse(clean["has_anomaly"])
        self.assertTrue(anomalous["has_anomaly"])

    def test_retry_wrapper_retries_until_success(self):
        class FlakyChain:
            def __init__(self):
                self.calls = 0

            async def ainvoke(self, inputs):
                self.calls += 1
                if self.calls < 3:
                    raise RuntimeError("temporary")
                return "ok"

        chain = FlakyChain()

        result = asyncio.run(safe_llm_call(chain, {}))

        self.assertEqual(result, "ok")
        self.assertEqual(chain.calls, 3)


if __name__ == "__main__":
    unittest.main()
