-- Step 13 additive migration. Safe to run after 001_schema.sql on an existing database.
USE municipal_ops;

ALTER TABLE inspection_tasks ADD COLUMN IF NOT EXISTS result_notes TEXT;
ALTER TABLE inspection_tasks ADD COLUMN IF NOT EXISTS defer_reason TEXT;

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
