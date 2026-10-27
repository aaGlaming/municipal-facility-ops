-- Step 19 additive migration for existing databases.
USE municipal_ops;

ALTER TABLE tool_calls ADD COLUMN IF NOT EXISTS human_confirmation BOOLEAN NOT NULL DEFAULT FALSE;
