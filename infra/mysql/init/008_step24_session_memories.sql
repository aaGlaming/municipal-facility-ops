USE municipal_ops;

CREATE TABLE IF NOT EXISTS session_memories (
  id VARCHAR(64) PRIMARY KEY,
  session_id VARCHAR(128) NOT NULL,
  user_id VARCHAR(128) NOT NULL,
  roles JSON NOT NULL,
  region VARCHAR(100),
  summary TEXT NOT NULL,
  messages JSON NOT NULL,
  evidence JSON NOT NULL,
  tool_results JSON NOT NULL,
  confirmations JSON NOT NULL,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NOT NULL,
  deleted_at TIMESTAMP NULL,
  KEY idx_memory_session (session_id, updated_at),
  KEY idx_memory_owner (user_id, region, updated_at),
  KEY idx_memory_expiry (expires_at, deleted_at)
);
