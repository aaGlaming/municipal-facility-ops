-- Municipal Facility Operations: Step 8 canonical MySQL schema.
-- This file creates structure only. Data loading belongs to Step 9.
CREATE DATABASE IF NOT EXISTS municipal_ops CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE municipal_ops;
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS users (
  id VARCHAR(64) PRIMARY KEY,
  username VARCHAR(128) NOT NULL,
  email VARCHAR(255),
  display_name VARCHAR(128) NOT NULL,
  password_hash VARCHAR(255),
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  region VARCHAR(100),
  source_type VARCHAR(32) NOT NULL DEFAULT 'internal',
  source_system VARCHAR(64) NOT NULL DEFAULT 'platform',
  data_version VARCHAR(64) NOT NULL DEFAULT 'v1',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_users_username (username),
  UNIQUE KEY uq_users_email (email),
  KEY idx_users_region_status (region, status),
  KEY idx_users_source_deleted (source_type, is_deleted)
);

CREATE TABLE IF NOT EXISTS roles (
  id VARCHAR(64) PRIMARY KEY,
  role_code VARCHAR(64) NOT NULL,
  name VARCHAR(128) NOT NULL,
  description VARCHAR(255),
  source_type VARCHAR(32) NOT NULL DEFAULT 'internal',
  source_system VARCHAR(64) NOT NULL DEFAULT 'platform',
  data_version VARCHAR(64) NOT NULL DEFAULT 'v1',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_roles_code (role_code),
  KEY idx_roles_deleted (is_deleted)
);

CREATE TABLE IF NOT EXISTS permissions (
  id VARCHAR(64) PRIMARY KEY,
  permission_code VARCHAR(128) NOT NULL,
  description VARCHAR(255),
  source_type VARCHAR(32) NOT NULL DEFAULT 'internal',
  source_system VARCHAR(64) NOT NULL DEFAULT 'platform',
  data_version VARCHAR(64) NOT NULL DEFAULT 'v1',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_permissions_code (permission_code),
  KEY idx_permissions_deleted (is_deleted)
);

CREATE TABLE IF NOT EXISTS role_permissions (
  role_id VARCHAR(64) NOT NULL,
  permission_id VARCHAR(64) NOT NULL,
  granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (role_id, permission_id),
  CONSTRAINT fk_role_permissions_role FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
  CONSTRAINT fk_role_permissions_permission FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_roles (
  user_id VARCHAR(64) NOT NULL,
  role_id VARCHAR(64) NOT NULL,
  granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, role_id),
  CONSTRAINT fk_user_roles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_user_roles_role FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS locations (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  address VARCHAR(255) NOT NULL,
  district VARCHAR(100),
  region VARCHAR(100),
  longitude DECIMAL(10,7),
  latitude DECIMAL(10,7),
  external_id VARCHAR(128),
  source_type VARCHAR(32) NOT NULL,
  source_system VARCHAR(64) NOT NULL,
  data_version VARCHAR(64) NOT NULL DEFAULT 'v1',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_locations_source_external (source_system, external_id),
  KEY idx_locations_region (region),
  KEY idx_locations_coordinates (latitude, longitude),
  KEY idx_locations_source_deleted (source_type, is_deleted),
  CONSTRAINT ck_locations_latitude CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
  CONSTRAINT ck_locations_longitude CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
);

CREATE TABLE IF NOT EXISTS facilities (
  id VARCHAR(64) PRIMARY KEY,
  facility_code VARCHAR(100) NOT NULL,
  type VARCHAR(64) NOT NULL,
  name VARCHAR(255) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  criticality VARCHAR(32),
  location_id BIGINT,
  region VARCHAR(100),
  external_id VARCHAR(128),
  install_date DATE,
  condition_score TINYINT UNSIGNED,
  source_type VARCHAR(32) NOT NULL,
  source_system VARCHAR(64) NOT NULL,
  data_version VARCHAR(64) NOT NULL DEFAULT 'v1',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_facilities_code (facility_code),
  UNIQUE KEY uq_facilities_source_external (source_system, external_id),
  KEY idx_facilities_type_status (type, status),
  KEY idx_facilities_region_status (region, status),
  KEY idx_facilities_location (location_id),
  KEY idx_facilities_source_deleted (source_type, is_deleted),
  CONSTRAINT fk_facility_location FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS citizen_reports (
  id VARCHAR(64) PRIMARY KEY,
  facility_id VARCHAR(64),
  reporter_user_id VARCHAR(64),
  source VARCHAR(64) NOT NULL,
  description TEXT NOT NULL,
  category VARCHAR(64),
  subcategory VARCHAR(128),
  status VARCHAR(32) NOT NULL DEFAULT 'NEW',
  priority VARCHAR(16),
  external_id VARCHAR(128),
  source_type VARCHAR(32) NOT NULL,
  source_system VARCHAR(64) NOT NULL,
  data_version VARCHAR(64) NOT NULL DEFAULT 'v1',
  region VARCHAR(100),
  latitude DECIMAL(10,7),
  longitude DECIMAL(10,7),
  idempotency_key VARCHAR(255),
  reported_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  due_at DATETIME,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_report_source_external (source_system, external_id),
  UNIQUE KEY uq_report_idempotency (idempotency_key),
  KEY idx_reports_facility_status (facility_id, status),
  KEY idx_reports_region_created (region, reported_at),
  KEY idx_reports_status_due (status, due_at),
  KEY idx_reports_source_deleted (source_type, is_deleted),
  CONSTRAINT fk_report_facility FOREIGN KEY (facility_id) REFERENCES facilities(id) ON DELETE RESTRICT,
  CONSTRAINT fk_report_user FOREIGN KEY (reporter_user_id) REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT ck_reports_latitude CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
  CONSTRAINT ck_reports_longitude CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
);

CREATE TABLE IF NOT EXISTS technicians (
  id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  team VARCHAR(128),
  skill VARCHAR(128),
  region VARCHAR(100),
  active BOOLEAN NOT NULL DEFAULT TRUE,
  source_type VARCHAR(32) NOT NULL,
  source_system VARCHAR(64) NOT NULL,
  data_version VARCHAR(64) NOT NULL DEFAULT 'v1',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_technicians_region_active (region, active),
  KEY idx_technicians_skill_active (skill, active),
  KEY idx_technicians_source_deleted (source_type, is_deleted)
);

CREATE TABLE IF NOT EXISTS vendors (
  id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  capabilities JSON,
  sla_level VARCHAR(32),
  region VARCHAR(100),
  active BOOLEAN NOT NULL DEFAULT TRUE,
  source_type VARCHAR(32) NOT NULL,
  source_system VARCHAR(64) NOT NULL,
  data_version VARCHAR(64) NOT NULL DEFAULT 'v1',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_vendors_region_active (region, active),
  KEY idx_vendors_source_deleted (source_type, is_deleted)
);

CREATE TABLE IF NOT EXISTS sla_rules (
  id VARCHAR(64) PRIMARY KEY,
  category VARCHAR(64) NOT NULL,
  priority VARCHAR(16) NOT NULL,
  response_minutes INT UNSIGNED NOT NULL,
  resolution_minutes INT UNSIGNED NOT NULL,
  escalation_minutes INT UNSIGNED,
  region VARCHAR(100),
  source_type VARCHAR(32) NOT NULL,
  source_system VARCHAR(64) NOT NULL,
  data_version VARCHAR(64) NOT NULL DEFAULT 'v1',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_sla_category_priority (category, priority, region),
  KEY idx_sla_priority_region (priority, region),
  KEY idx_sla_source_deleted (source_type, is_deleted)
);

CREATE TABLE IF NOT EXISTS inspection_tasks (
  id VARCHAR(64) PRIMARY KEY,
  facility_id VARCHAR(64),
  area VARCHAR(128),
  priority VARCHAR(16),
  scheduled_at DATETIME,
  due_at DATETIME,
  completed_at DATETIME,
  assignee_id VARCHAR(64),
  status VARCHAR(32) NOT NULL,
  region VARCHAR(100),
  result_notes TEXT,
  defer_reason TEXT,
  source_type VARCHAR(32) NOT NULL,
  source_system VARCHAR(64) NOT NULL,
  data_version VARCHAR(64) NOT NULL DEFAULT 'v1',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_inspection_schedule_status (scheduled_at, status),
  KEY idx_inspection_facility_status (facility_id, status),
  KEY idx_inspection_assignee_due (assignee_id, due_at),
  KEY idx_inspection_source_deleted (source_type, is_deleted),
  CONSTRAINT fk_inspection_facility FOREIGN KEY (facility_id) REFERENCES facilities(id) ON DELETE RESTRICT,
  CONSTRAINT fk_inspection_technician FOREIGN KEY (assignee_id) REFERENCES technicians(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS work_orders (
  id VARCHAR(64) PRIMARY KEY,
  report_id VARCHAR(64),
  facility_id VARCHAR(64),
  priority VARCHAR(16) NOT NULL,
  problem_type VARCHAR(64),
  assignee_id VARCHAR(64),
  vendor_id VARCHAR(64),
  due_at DATETIME,
  completed_at DATETIME,
  status VARCHAR(32) NOT NULL,
  idempotency_key VARCHAR(255) NOT NULL,
  region VARCHAR(100),
  source_type VARCHAR(32) NOT NULL,
  source_system VARCHAR(64) NOT NULL,
  data_version VARCHAR(64) NOT NULL DEFAULT 'v1',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_work_order_idempotency (idempotency_key),
  KEY idx_work_order_status_due (status, due_at),
  KEY idx_work_order_facility_status (facility_id, status),
  KEY idx_work_order_report (report_id),
  KEY idx_work_order_assignee_due (assignee_id, due_at),
  KEY idx_work_order_vendor_status (vendor_id, status),
  KEY idx_work_order_source_deleted (source_type, is_deleted),
  CONSTRAINT fk_order_report FOREIGN KEY (report_id) REFERENCES citizen_reports(id) ON DELETE RESTRICT,
  CONSTRAINT fk_order_facility FOREIGN KEY (facility_id) REFERENCES facilities(id) ON DELETE RESTRICT,
  CONSTRAINT fk_order_technician FOREIGN KEY (assignee_id) REFERENCES technicians(id) ON DELETE SET NULL,
  CONSTRAINT fk_order_vendor FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS acceptance_records (
  id VARCHAR(64) PRIMARY KEY,
  work_order_id VARCHAR(64) NOT NULL,
  reviewer_id VARCHAR(64),
  result VARCHAR(32) NOT NULL,
  reason TEXT,
  evidence_uri VARCHAR(1024),
  source_type VARCHAR(32) NOT NULL DEFAULT 'internal',
  source_system VARCHAR(64) NOT NULL DEFAULT 'platform',
  data_version VARCHAR(64) NOT NULL DEFAULT 'v1',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_acceptance_order_result (work_order_id, result),
  KEY idx_acceptance_reviewer_time (reviewer_id, created_at),
  CONSTRAINT fk_acceptance_order FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE RESTRICT,
  CONSTRAINT fk_acceptance_reviewer FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS work_order_status_events (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  work_order_id VARCHAR(64) NOT NULL,
  idempotency_key VARCHAR(255) NOT NULL,
  from_status VARCHAR(32) NOT NULL,
  to_status VARCHAR(32) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_status_event_idempotency (idempotency_key),
  KEY idx_status_event_order_time (work_order_id, created_at)
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id VARCHAR(64) PRIMARY KEY,
  agent_name VARCHAR(64) NOT NULL,
  trace_id VARCHAR(128) NOT NULL,
  user_id VARCHAR(64),
  region VARCHAR(100),
  status VARCHAR(32) NOT NULL,
  iterations INT UNSIGNED NOT NULL DEFAULT 0,
  input_tokens INT UNSIGNED NOT NULL DEFAULT 0,
  output_tokens INT UNSIGNED NOT NULL DEFAULT 0,
  model_version VARCHAR(128),
  prompt_version VARCHAR(128),
  stop_reason VARCHAR(255),
  source_type VARCHAR(32) NOT NULL DEFAULT 'internal',
  source_system VARCHAR(64) NOT NULL DEFAULT 'platform',
  data_version VARCHAR(64) NOT NULL DEFAULT 'v1',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TIMESTAMP NULL,
  KEY idx_agent_trace (trace_id),
  KEY idx_agent_status_started (status, started_at),
  KEY idx_agent_user_region (user_id, region),
  KEY idx_agent_source_deleted (source_type, is_deleted),
  CONSTRAINT fk_agent_run_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS tool_calls (
  id VARCHAR(64) PRIMARY KEY,
  agent_run_id VARCHAR(64) NOT NULL,
  tool_name VARCHAR(128) NOT NULL,
  action VARCHAR(128) NOT NULL,
  risk_level VARCHAR(32) NOT NULL DEFAULT 'low',
  status VARCHAR(32) NOT NULL,
  idempotency_key VARCHAR(255),
  request_json JSON,
  response_json JSON,
  error TEXT,
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TIMESTAMP NULL,
  KEY idx_tool_agent_started (agent_run_id, started_at),
  KEY idx_tool_name_status (tool_name, status),
  KEY idx_tool_risk_status (risk_level, status),
  UNIQUE KEY uq_tool_call_idempotency (agent_run_id, idempotency_key),
  CONSTRAINT fk_tool_call_run FOREIGN KEY (agent_run_id) REFERENCES agent_runs(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  actor_user_id VARCHAR(64),
  actor VARCHAR(128),
  agent_run_id VARCHAR(64),
  tool_call_id VARCHAR(64),
  tool_name VARCHAR(128),
  action VARCHAR(128) NOT NULL,
  resource_type VARCHAR(64),
  resource_id VARCHAR(128),
  before_json JSON,
  after_json JSON,
  result VARCHAR(32),
  risk_level VARCHAR(32) NOT NULL DEFAULT 'low',
  error TEXT,
  human_confirmation BOOLEAN NOT NULL DEFAULT FALSE,
  event_version VARCHAR(64) NOT NULL DEFAULT 'v1',
  event_hash CHAR(64),
  previous_event_hash CHAR(64),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_audit_event_hash (event_hash),
  KEY idx_audit_resource_time (resource_type, resource_id, created_at),
  KEY idx_audit_actor_time (actor_user_id, created_at),
  KEY idx_audit_run (agent_run_id),
  KEY idx_audit_tool (tool_call_id),
  KEY idx_audit_risk_time (risk_level, created_at),
  CONSTRAINT fk_audit_user FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT fk_audit_run FOREIGN KEY (agent_run_id) REFERENCES agent_runs(id) ON DELETE SET NULL,
  CONSTRAINT fk_audit_tool FOREIGN KEY (tool_call_id) REFERENCES tool_calls(id) ON DELETE SET NULL
);

DROP TRIGGER IF EXISTS trg_audit_logs_no_update;
DROP TRIGGER IF EXISTS trg_audit_logs_no_delete;
DELIMITER //
CREATE TRIGGER trg_audit_logs_no_update
BEFORE UPDATE ON audit_logs
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit_logs is append-only';
END//
CREATE TRIGGER trg_audit_logs_no_delete
BEFORE DELETE ON audit_logs
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit_logs is append-only';
END//
DELIMITER ;
