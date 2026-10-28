-- Step 19 additive migration for existing databases.
USE municipal_ops;

-- MySQL 8.4 does not support ALTER TABLE ... ADD COLUMN IF NOT EXISTS.
SET @step19_confirmation_sql = (
  SELECT IF(COUNT(*) = 0,
    'ALTER TABLE tool_calls ADD COLUMN human_confirmation BOOLEAN NOT NULL DEFAULT FALSE',
    'SELECT 1')
  FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'tool_calls' AND column_name = 'human_confirmation'
);
PREPARE step19_confirmation_stmt FROM @step19_confirmation_sql;
EXECUTE step19_confirmation_stmt;
DEALLOCATE PREPARE step19_confirmation_stmt;
