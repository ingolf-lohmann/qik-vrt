-- Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- PREPARED SOURCE ONLY. Not executed against the Cloud service.
-- Query patterns: exact repository + run head + bounded observation time;
-- latest platform state per run/attempt; failed workflows; event distribution.
-- No TTL: original evidence retention has not been replaced by an analytics policy.
CREATE DATABASE IF NOT EXISTS qikvrt_devops;

CREATE TABLE IF NOT EXISTS qikvrt_devops.workflow_observations
(
    repository LowCardinality(String),
    run_id UInt64,
    attempt UInt32,
    run_head FixedString(40),
    repository_head String COMMENT 'Head at observation; empty means unknown',
    workflow_name String,
    event LowCardinality(String),
    status LowCardinality(String),
    conclusion LowCardinality(String),
    source_updated_at DateTime64(3, 'UTC'),
    source_observed_at DateTime64(3, 'UTC'),
    started_at Nullable(DateTime64(3, 'UTC')) COMMENT 'Unknown is not epoch zero',
    source_url String,
    source_endpoint String,
    source_complete Bool,
    projection_sha256 FixedString(64) COMMENT 'Digest of canonical exported projection, not wire-byte attestation',
    CONSTRAINT valid_attempt CHECK attempt > 0,
    CONSTRAINT valid_head CHECK match(run_head, '^[a-f0-9]{40}$'),
    CONSTRAINT valid_repository_head CHECK repository_head = '' OR match(repository_head, '^[a-f0-9]{40}$'),
    CONSTRAINT valid_digest CHECK match(projection_sha256, '^[a-f0-9]{64}$')
)
ENGINE = MergeTree
ORDER BY (repository, run_head, source_observed_at, run_id, attempt);

-- Append-only observations. Deduplicate snapshots before counting workflows.
-- A replay cannot override newer provider state by acquiring a newer receive time.
-- Keep each attempt distinct; technical workflow success is not EFFECT_ACK_DONE.
CREATE VIEW IF NOT EXISTS qikvrt_devops.workflow_latest AS
SELECT repository, run_id, attempt,
    argMax(tuple(run_head, workflow_name, event, status, conclusion,
                 source_updated_at, source_observed_at, started_at, source_url,
                 repository_head, source_complete),
           tuple(source_updated_at, source_observed_at, projection_sha256)) AS observation
FROM qikvrt_devops.workflow_observations
GROUP BY repository, run_id, attempt;

-- Run only after schema discovery and actual source import/readback.
-- JSONEachRow insert uses date_time_input_format='best_effort',
-- async_insert=1, wait_for_async_insert=1. No automatic insertion is performed.
-- Example bounded view of observations (replace the exact head before use):
-- SELECT run_id, attempt,
--   argMax(tuple(workflow_name,status,conclusion,source_url),
--     tuple(source_updated_at,source_observed_at,projection_sha256)) AS latest
-- FROM qikvrt_devops.workflow_observations
-- WHERE repository = 'ingolf-lohmann/qik-vrt'
--   AND run_head = {head:String}
--   AND source_observed_at >= now() - INTERVAL 7 DAY
-- GROUP BY run_id, attempt ORDER BY run_id DESC LIMIT 100
-- SETTINGS max_execution_time=10, timeout_before_checking_execution_speed=0,
--   max_rows_to_read=1000000, max_bytes_to_read=100000000;
