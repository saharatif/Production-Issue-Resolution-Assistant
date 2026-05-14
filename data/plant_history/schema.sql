CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS plants (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  location TEXT NOT NULL,
  timezone TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS production_lines (
  id TEXT PRIMARY KEY,
  plant_id TEXT NOT NULL REFERENCES plants(id),
  name TEXT NOT NULL,
  product_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quality_thresholds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  line_id TEXT NOT NULL REFERENCES production_lines(id),
  metric TEXT NOT NULL,
  warning_low NUMERIC,
  warning_high NUMERIC,
  critical_low NUMERIC,
  critical_high NUMERIC,
  unit TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS maintenance_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  line_id TEXT NOT NULL REFERENCES production_lines(id),
  machine_id TEXT NOT NULL,
  event_date DATE NOT NULL,
  event_type TEXT NOT NULL,
  description TEXT NOT NULL,
  resolved_by TEXT,
  resolution_note TEXT
);

CREATE TABLE IF NOT EXISTS production_issues (
  issue_id TEXT PRIMARY KEY,
  plant_id TEXT NOT NULL,
  line_id TEXT NOT NULL,
  problem_statement TEXT NOT NULL,
  timeframe_start TIMESTAMP,
  timeframe_end TIMESTAMP,
  severity TEXT,
  status TEXT NOT NULL DEFAULT 'RUNNING',
  approval_status TEXT NOT NULL DEFAULT 'pending',
  approver TEXT,
  approval_notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS anomaly_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id TEXT NOT NULL REFERENCES production_issues(issue_id),
  machine_id TEXT,
  anomaly_type TEXT NOT NULL,
  metric_name TEXT,
  metric_value NUMERIC,
  threshold_value NUMERIC,
  timestamp TIMESTAMP,
  severity TEXT
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id TEXT NOT NULL REFERENCES production_issues(issue_id),
  scanner_output JSONB,
  investigator_output JSONB,
  technician_output JSONB,
  retrieved_context TEXT,
  pdf_path TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS maintenance_requests (
  request_id TEXT PRIMARY KEY,
  issue_id TEXT NOT NULL REFERENCES production_issues(issue_id),
  asset_id TEXT NOT NULL,
  priority TEXT NOT NULL,
  request_text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'PENDING',
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  actor TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is immutable';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_log_no_update ON audit_log;
CREATE TRIGGER audit_log_no_update
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();
