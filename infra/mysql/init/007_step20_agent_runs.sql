USE municipal_ops;

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
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TIMESTAMP NULL,
  KEY idx_agent_trace (trace_id),
  KEY idx_agent_status_started (status, started_at)
);
