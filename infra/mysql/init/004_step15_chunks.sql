-- Step 15 additive migration for existing databases.
USE municipal_ops;

CREATE TABLE IF NOT EXISTS document_chunks (
  id VARCHAR(64) PRIMARY KEY,
  document_id VARCHAR(64) NOT NULL,
  chunk_index INT UNSIGNED NOT NULL,
  text LONGTEXT NOT NULL,
  token_count INT UNSIGNED NOT NULL,
  page_number INT UNSIGNED,
  heading VARCHAR(512),
  source_part_id VARCHAR(64),
  start_offset INT UNSIGNED NOT NULL,
  end_offset INT UNSIGNED NOT NULL,
  target_tokens INT UNSIGNED NOT NULL,
  overlap_tokens INT UNSIGNED NOT NULL,
  cleaning_version VARCHAR(64) NOT NULL DEFAULT 'step15-v1',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_document_chunk_index (document_id, chunk_index),
  KEY idx_document_chunks_document (document_id, chunk_index),
  CONSTRAINT fk_document_chunk_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
