-- Step 16 additive migration for existing databases.
USE municipal_ops;

-- MySQL 8.4 does not support ALTER TABLE ... ADD COLUMN IF NOT EXISTS.
SET @step16_embedding_status_sql = (
  SELECT IF(COUNT(*) = 0,
    'ALTER TABLE document_chunks ADD COLUMN embedding_status VARCHAR(32) NOT NULL DEFAULT ''PENDING''',
    'SELECT 1')
  FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'document_chunks' AND column_name = 'embedding_status'
);
PREPARE step16_embedding_status_stmt FROM @step16_embedding_status_sql;
EXECUTE step16_embedding_status_stmt;
DEALLOCATE PREPARE step16_embedding_status_stmt;

SET @step16_embedding_batch_sql = (
  SELECT IF(COUNT(*) = 0, 'ALTER TABLE document_chunks ADD COLUMN embedding_batch_id VARCHAR(64)', 'SELECT 1')
  FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'document_chunks' AND column_name = 'embedding_batch_id'
);
PREPARE step16_embedding_batch_stmt FROM @step16_embedding_batch_sql;
EXECUTE step16_embedding_batch_stmt;
DEALLOCATE PREPARE step16_embedding_batch_stmt;

SET @step16_embedding_model_sql = (
  SELECT IF(COUNT(*) = 0, 'ALTER TABLE document_chunks ADD COLUMN embedding_model VARCHAR(255)', 'SELECT 1')
  FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'document_chunks' AND column_name = 'embedding_model'
);
PREPARE step16_embedding_model_stmt FROM @step16_embedding_model_sql;
EXECUTE step16_embedding_model_stmt;
DEALLOCATE PREPARE step16_embedding_model_stmt;

CREATE TABLE IF NOT EXISTS embedding_batches (
  id VARCHAR(64) PRIMARY KEY,
  document_id VARCHAR(64) NOT NULL,
  model_name VARCHAR(255) NOT NULL,
  status VARCHAR(32) NOT NULL,
  chunk_count INT UNSIGNED NOT NULL,
  embedded_count INT UNSIGNED NOT NULL DEFAULT 0,
  attempt_count INT UNSIGNED NOT NULL DEFAULT 0,
  error_reason TEXT,
  retryable BOOLEAN NOT NULL DEFAULT TRUE,
  document_version VARCHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TIMESTAMP NULL,
  KEY idx_embedding_batch_document (document_id, created_at),
  KEY idx_embedding_batch_status (status, created_at)
);
