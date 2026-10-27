-- Step 16 additive migration for existing databases.
USE municipal_ops;

ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_status VARCHAR(32) NOT NULL DEFAULT 'PENDING';
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_batch_id VARCHAR(64);
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(255);

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
