import unittest

from app.services.simulation_service import (
    demo_scenario_line_b_pressure_drop,
    generate_batch,
    generate_scenario_batch,
)


class SimulationServiceTest(unittest.TestCase):
    def test_generate_batch_returns_one_reading_per_line(self):
        batch = generate_batch(anomaly_probability=0)

        self.assertEqual(len(batch), 4)
        self.assertEqual(
            {reading["line_id"] for reading in batch},
            {"LINE-A", "LINE-B", "LINE-C", "LINE-D"},
        )
        self.assertTrue(all(reading["machine_status"] == "RUNNING" for reading in batch))

    def test_generate_batch_validates_probability(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            generate_batch(anomaly_probability=1.5)

    def test_demo_scenario_line_b_pressure_drop_is_deterministic_for_line_b(self):
        batch = demo_scenario_line_b_pressure_drop()
        line_b = next(reading for reading in batch if reading["line_id"] == "LINE-B")

        self.assertEqual(len(batch), 4)
        self.assertEqual(line_b["machine_id"], "PRESS-VALVE-23")
        self.assertEqual(line_b["machine_status"], "RUNNING_WITH_WARNING")
        self.assertGreaterEqual(line_b["pressure_bar"], 0.05)
        self.assertLessEqual(line_b["pressure_bar"], 0.15)
        self.assertGreaterEqual(line_b["output_units_per_hour"], 450)
        self.assertLessEqual(line_b["output_units_per_hour"], 620)

    def test_generate_scenario_batch_live_returns_four_readings(self):
        for scenario in ("live", "", "unknown_scenario"):
            batch = generate_scenario_batch(scenario)
            self.assertEqual(len(batch), 4, f"Expected 4 readings for scenario '{scenario}'")

    def test_generate_scenario_batch_pressure_drop_targets_line_b(self):
        batch = generate_scenario_batch("pressure_drop")
        line_b = next(reading for reading in batch if reading["line_id"] == "LINE-B")

        self.assertEqual(line_b["machine_status"], "RUNNING_WITH_WARNING")
        self.assertGreaterEqual(line_b["pressure_bar"], 0.05)
        self.assertLessEqual(line_b["pressure_bar"], 0.15)

    def test_generate_scenario_batch_temp_spike_targets_line_a(self):
        batch = generate_scenario_batch("temp_spike")
        line_a = next(reading for reading in batch if reading["line_id"] == "LINE-A")

        self.assertEqual(line_a["machine_status"], "CRITICAL_TEMPERATURE_SPIKE")
        self.assertGreaterEqual(line_a["temperature_c"], 280.0)
        self.assertLessEqual(line_a["temperature_c"], 320.0)

    def test_generate_scenario_batch_data_gap_targets_line_c(self):
        batch = generate_scenario_batch("data_gap")
        line_c = next(reading for reading in batch if reading["line_id"] == "LINE-C")

        self.assertEqual(line_c["machine_status"], "DATA_GAP")
        self.assertIsNone(line_c["temperature_c"])
        self.assertIsNone(line_c["pressure_bar"])
        self.assertIsNone(line_c["vibration_mm_s"])
        self.assertIsNone(line_c["output_units_per_hour"])

    def test_generate_scenario_batch_does_not_mutate_other_lines(self):
        expected_target_by_scenario = {
            "pressure_drop": "LINE-B",
            "temp_spike": "LINE-A",
            "data_gap": "LINE-C",
            "high_vibration": "LINE-C",
        }
        for scenario, expected_target in expected_target_by_scenario.items():
            batch = generate_scenario_batch(scenario)
            other_lines = [r for r in batch if r["line_id"] != expected_target]
            for reading in other_lines:
                self.assertEqual(
                    reading["machine_status"],
                    "RUNNING",
                    f"Non-target reading had unexpected status in scenario '{scenario}'",
                )

    def test_internal_anomaly_tag_not_exposed(self):
        for fn in (generate_batch, demo_scenario_line_b_pressure_drop):
            batch = fn() if fn is demo_scenario_line_b_pressure_drop else fn(anomaly_probability=1.0)
            for reading in batch:
                self.assertNotIn("_anomaly_tag", reading)


if __name__ == "__main__":
    unittest.main()
