BEGIN;

-- ── Schema ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS plants (
    id       TEXT PRIMARY KEY,
    name     TEXT NOT NULL,
    location TEXT NOT NULL,
    timezone TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS production_lines (
    id           TEXT PRIMARY KEY,
    plant_id     TEXT NOT NULL REFERENCES plants(id),
    name         TEXT NOT NULL,
    product_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quality_thresholds (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_id       TEXT NOT NULL REFERENCES production_lines(id),
    metric        TEXT NOT NULL,
    warning_low   DOUBLE PRECISION NOT NULL,
    warning_high  DOUBLE PRECISION NOT NULL,
    critical_low  DOUBLE PRECISION NOT NULL,
    critical_high DOUBLE PRECISION NOT NULL,
    unit          TEXT NOT NULL,
    UNIQUE (line_id, metric)
);

CREATE TABLE IF NOT EXISTS maintenance_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_id         TEXT NOT NULL REFERENCES production_lines(id),
    machine_id      TEXT NOT NULL,
    event_date      DATE NOT NULL,
    event_type      TEXT NOT NULL,
    description     TEXT NOT NULL,
    resolved_by     TEXT NOT NULL,
    resolution_note TEXT NOT NULL
);

-- ── Seed Data ─────────────────────────────────────────────────────────────────

INSERT INTO plants (id, name, location, timezone)
VALUES ('PLANT-01', 'Alpha Manufacturing - Dallas', 'Dallas, TX', 'America/Chicago')
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name,
    location = EXCLUDED.location,
    timezone = EXCLUDED.timezone;

INSERT INTO production_lines (id, plant_id, name, product_type)
VALUES
  ('LINE-A', 'PLANT-01', 'CNC Milling A', 'Precision Shafts'),
  ('LINE-B', 'PLANT-01', 'Hydraulic Press B', 'Automotive Body Panels'),
  ('LINE-C', 'PLANT-01', 'Spindle Machining C', 'Gear Components'),
  ('LINE-D', 'PLANT-01', 'Paint and Coating D', 'Surface Finishing')
ON CONFLICT (id) DO UPDATE
SET plant_id = EXCLUDED.plant_id,
    name = EXCLUDED.name,
    product_type = EXCLUDED.product_type;

INSERT INTO quality_thresholds
  (line_id, metric, warning_low, warning_high, critical_low, critical_high, unit)
VALUES
  ('LINE-A', 'temperature_c', 65.0, 90.0, 55.0, 150.0, 'C'),
  ('LINE-A', 'pressure_bar', 4.8, 6.5, 3.5, 8.0, 'bar'),
  ('LINE-A', 'vibration_mm_s', 1.0, 4.0, 0.5, 8.0, 'mm/s'),
  ('LINE-A', 'output_units_per_hour', 700.0, 1100.0, 500.0, 1200.0, 'units/hr'),
  ('LINE-B', 'temperature_c', 65.0, 90.0, 55.0, 150.0, 'C'),
  ('LINE-B', 'pressure_bar', 4.8, 6.5, 3.5, 8.0, 'bar'),
  ('LINE-B', 'vibration_mm_s', 1.0, 4.0, 0.5, 8.0, 'mm/s'),
  ('LINE-B', 'output_units_per_hour', 700.0, 1100.0, 500.0, 1200.0, 'units/hr'),
  ('LINE-C', 'temperature_c', 65.0, 90.0, 55.0, 150.0, 'C'),
  ('LINE-C', 'pressure_bar', 4.8, 6.5, 3.5, 8.0, 'bar'),
  ('LINE-C', 'vibration_mm_s', 1.0, 4.0, 0.5, 8.0, 'mm/s'),
  ('LINE-C', 'output_units_per_hour', 700.0, 1100.0, 500.0, 1200.0, 'units/hr'),
  ('LINE-D', 'temperature_c', 65.0, 90.0, 55.0, 150.0, 'C'),
  ('LINE-D', 'pressure_bar', 4.8, 6.5, 3.5, 8.0, 'bar'),
  ('LINE-D', 'vibration_mm_s', 1.0, 4.0, 0.5, 8.0, 'mm/s'),
  ('LINE-D', 'output_units_per_hour', 700.0, 1100.0, 500.0, 1200.0, 'units/hr')
ON CONFLICT DO NOTHING;

INSERT INTO maintenance_history
  (line_id, machine_id, event_date, event_type, description, resolved_by, resolution_note)
VALUES
  (
    'LINE-B',
    'PRESS-VALVE-23',
    '2026-03-12',
    'corrective',
    'Pressure dropped below operating threshold. Output decreased 38 percent.',
    'Technician A',
    'Pressure valve recalibrated and actuator response verified. Output restored within 2 hours.'
  ),
  (
    'LINE-B',
    'PRESS-VALVE-23',
    '2026-04-28',
    'preventive',
    'Minor actuator response delay observed during pressure ramp test.',
    'Technician A',
    'Valve cleaned and response tested. Follow-up calibration recommended at next planned downtime.'
  ),
  (
    'LINE-A',
    'CNC-MILL-11',
    '2026-01-05',
    'corrective',
    'Temperature spike to 295 C on roller bearing housing. Lubrication line blocked.',
    'Technician B',
    'Purged lubrication line. Replaced bearing assembly. Temperature returned to nominal range.'
  ),
  (
    'LINE-C',
    'SPINDLE-07',
    '2026-03-18',
    'preventive',
    'Scheduled vibration analysis found early-stage bearing degradation at spindle motor 2.',
    'Technician C',
    'Preemptive bearing swap completed with zero downtime impact.'
  );

COMMIT;
