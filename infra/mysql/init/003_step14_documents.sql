-- Step 14 additive migration for existing databases.
USE municipal_ops;

CREATE TABLE IF NOT EXISTS documents (
  id VARCHAR(64) PRIMARY KEY,
  original_filename VARCHAR(255) NOT NULL,
  storage_key VARCHAR(512) NOT NULL,
  media_type VARCHAR(128) NOT NULL,
  extension VARCHAR(16) NOT NULL,
  size_bytes INT UNSIGNED NOT NULL,
  sha256 CHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL,
  error_reason TEXT,
  uploaded_by VARCHAR(128) NOT NULL,
  facility_type VARCHAR(64),
  region VARCHAR(100),
  effective_date DATE,
  expiry_date DATE,
  version VARCHAR(64) NOT NULL DEFAULT 'v1',
  source_type VARCHAR(32) NOT NULL,
  source_system VARCHAR(64) NOT NULL,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_documents_sha256 (sha256),
  KEY idx_documents_status (status),
  KEY idx_documents_region_type (region, facility_type),
  KEY idx_documents_source_deleted (source_type, is_deleted)
);

CREATE TABLE IF NOT EXISTS document_parts (
  id VARCHAR(64) PRIMARY KEY,
  document_id VARCHAR(64) NOT NULL,
  part_index INT UNSIGNED NOT NULL,
  page_number INT UNSIGNED,
  heading VARCHAR(512),
  text LONGTEXT NOT NULL,
  source_location VARCHAR(255),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_document_part_index (document_id, part_index),
  KEY idx_document_parts_document (document_id, part_index),
  CONSTRAINT fk_document_part_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
