CREATE DATABASE IF NOT EXISTS municipal_ops CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE municipal_ops;

CREATE TABLE IF NOT EXISTS locations (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  address VARCHAR(255) NOT NULL,
  district VARCHAR(100), longitude DECIMAL(10,7), latitude DECIMAL(10,7),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS facilities (
  id VARCHAR(64) PRIMARY KEY, facility_code VARCHAR(100) UNIQUE, type VARCHAR(64) NOT NULL,
  name VARCHAR(255) NOT NULL, status VARCHAR(32) NOT NULL DEFAULT 'active', criticality VARCHAR(32),
  location_id BIGINT, source_type VARCHAR(32) NOT NULL, external_id VARCHAR(128),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_facility_type_status (type, status), INDEX idx_facility_source (source_type),
  CONSTRAINT fk_facility_location FOREIGN KEY (location_id) REFERENCES locations(id)
);

CREATE TABLE IF NOT EXISTS citizen_reports (
  id VARCHAR(64) PRIMARY KEY, facility_id VARCHAR(64), source VARCHAR(64) NOT NULL, description TEXT NOT NULL,
  category VARCHAR(64), status VARCHAR(32) NOT NULL DEFAULT 'NEW', external_id VARCHAR(128), source_type VARCHAR(32) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_report_source_external (source, external_id), INDEX idx_report_status (status),
  CONSTRAINT fk_report_facility FOREIGN KEY (facility_id) REFERENCES facilities(id)
);

CREATE TABLE IF NOT EXISTS technicians (
  id VARCHAR(64) PRIMARY KEY, name VARCHAR(128) NOT NULL, team VARCHAR(128), skill VARCHAR(128),
  active BOOLEAN NOT NULL DEFAULT TRUE, source_type VARCHAR(32) NOT NULL
);

CREATE TABLE IF NOT EXISTS vendors (
  id VARCHAR(64) PRIMARY KEY, name VARCHAR(255) NOT NULL, capabilities JSON, sla_level VARCHAR(32),
  active BOOLEAN NOT NULL DEFAULT TRUE, source_type VARCHAR(32) NOT NULL
);

CREATE TABLE IF NOT EXISTS sla_rules (
  id VARCHAR(64) PRIMARY KEY, category VARCHAR(64) NOT NULL, priority VARCHAR(16) NOT NULL,
  response_minutes INT NOT NULL, resolution_minutes INT NOT NULL, source_type VARCHAR(32) NOT NULL,
  UNIQUE KEY uq_sla_category_priority (category, priority)
);

CREATE TABLE IF NOT EXISTS inspection_tasks (
  id VARCHAR(64) PRIMARY KEY, facility_id VARCHAR(64), area VARCHAR(128), scheduled_at DATETIME,
  assignee_id VARCHAR(64), status VARCHAR(32) NOT NULL, source_type VARCHAR(32) NOT NULL,
  INDEX idx_inspection_schedule (scheduled_at, status),
  CONSTRAINT fk_inspection_facility FOREIGN KEY (facility_id) REFERENCES facilities(id)
);

CREATE TABLE IF NOT EXISTS work_orders (
  id VARCHAR(64) PRIMARY KEY, report_id VARCHAR(64), facility_id VARCHAR(64), priority VARCHAR(16) NOT NULL,
  assignee_id VARCHAR(64), vendor_id VARCHAR(64), due_at DATETIME, status VARCHAR(32) NOT NULL,
  idempotency_key VARCHAR(255) NOT NULL UNIQUE, source_type VARCHAR(32) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_work_order_status_due (status, due_at), INDEX idx_work_order_facility (facility_id),
  CONSTRAINT fk_order_report FOREIGN KEY (report_id) REFERENCES citizen_reports(id),
  CONSTRAINT fk_order_facility FOREIGN KEY (facility_id) REFERENCES facilities(id),
  CONSTRAINT fk_order_technician FOREIGN KEY (assignee_id) REFERENCES technicians(id),
  CONSTRAINT fk_order_vendor FOREIGN KEY (vendor_id) REFERENCES vendors(id)
);

CREATE TABLE IF NOT EXISTS acceptance_records (
  id VARCHAR(64) PRIMARY KEY, work_order_id VARCHAR(64) NOT NULL, reviewer_id VARCHAR(64), result VARCHAR(32) NOT NULL,
  reason TEXT, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_acceptance_order FOREIGN KEY (work_order_id) REFERENCES work_orders(id)
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id VARCHAR(64) PRIMARY KEY, agent_name VARCHAR(64) NOT NULL, trace_id VARCHAR(128) NOT NULL,
  status VARCHAR(32) NOT NULL, iterations INT DEFAULT 0, input_tokens INT DEFAULT 0, output_tokens INT DEFAULT 0,
  stop_reason VARCHAR(255), started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, finished_at TIMESTAMP NULL,
  INDEX idx_agent_trace (trace_id), INDEX idx_agent_status (status)
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT, actor VARCHAR(128), agent_run_id VARCHAR(64), tool_name VARCHAR(128),
  action VARCHAR(128) NOT NULL, resource VARCHAR(128), before_json JSON, after_json JSON, result VARCHAR(32),
  error TEXT, human_confirmation BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_audit_resource_time (resource, created_at), INDEX idx_audit_run (agent_run_id),
  CONSTRAINT fk_audit_run FOREIGN KEY (agent_run_id) REFERENCES agent_runs(id)
);
