-- Step 13 additive migration. Safe to run after 001_schema.sql on an existing database.
USE municipal_ops;

-- MySQL 8.4 does not support ALTER TABLE ... ADD COLUMN IF NOT EXISTS.
-- Use metadata checks so this migration remains safe for older databases.
SET @step13_result_notes_sql = (
  SELECT IF(COUNT(*) = 0, 'ALTER TABLE inspection_tasks ADD COLUMN result_notes TEXT', 'SELECT 1')
  FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'inspection_tasks' AND column_name = 'result_notes'
);
PREPARE step13_result_notes_stmt FROM @step13_result_notes_sql;
EXECUTE step13_result_notes_stmt;
DEALLOCATE PREPARE step13_result_notes_stmt;

SET @step13_defer_reason_sql = (
  SELECT IF(COUNT(*) = 0, 'ALTER TABLE inspection_tasks ADD COLUMN defer_reason TEXT', 'SELECT 1')
  FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'inspection_tasks' AND column_name = 'defer_reason'
);
PREPARE step13_defer_reason_stmt FROM @step13_defer_reason_sql;
EXECUTE step13_defer_reason_stmt;
DEALLOCATE PREPARE step13_defer_reason_stmt;

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
