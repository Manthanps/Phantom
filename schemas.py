"""SQL DDL for all GhostFlow tables. Imported by MigrationManager."""

MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS _migrations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_id  TEXT    UNIQUE,
    name          TEXT    UNIQUE NOT NULL,
    applied_at    TEXT    NOT NULL,
    checksum      TEXT    NOT NULL DEFAULT ''
)
"""

# ── events ────────────────────────────────────────────────────────────────────

EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id      TEXT    UNIQUE NOT NULL,
    session_id    TEXT,
    timestamp     TEXT    NOT NULL,
    event_type    TEXT    NOT NULL,
    source        TEXT    NOT NULL,
    path          TEXT,
    old_path      TEXT,
    observer_name TEXT,
    host_name     TEXT,
    metadata_json TEXT,
    created_at    TEXT    NOT NULL
)
"""

EVENTS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_events_event_id   ON events(event_id)",
    "CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_events_timestamp  ON events(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type)",
    "CREATE INDEX IF NOT EXISTS idx_events_path       ON events(path)",
]

# ── sessions ──────────────────────────────────────────────────────────────────

SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT    UNIQUE NOT NULL,
    started_at    TEXT    NOT NULL,
    ended_at      TEXT,
    event_count   INTEGER DEFAULT 0,
    status        TEXT    NOT NULL,
    metadata_json TEXT,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
)
"""

SESSIONS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sessions_session_id  ON sessions(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_started_at  ON sessions(started_at)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_status      ON sessions(status)",
]

# ── workflow_candidates ───────────────────────────────────────────────────────

WORKFLOW_CANDIDATES_TABLE = """
CREATE TABLE IF NOT EXISTS workflow_candidates (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id         TEXT    UNIQUE NOT NULL,
    name                 TEXT,
    confidence           REAL    NOT NULL,
    frequency            INTEGER NOT NULL,
    event_sequence_json  TEXT    NOT NULL,
    first_seen_at        TEXT,
    last_seen_at         TEXT,
    status               TEXT    NOT NULL,
    metadata_json        TEXT,
    created_at           TEXT    NOT NULL,
    updated_at           TEXT    NOT NULL
)
"""

WORKFLOW_CANDIDATES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_workflow_candidates_candidate_id ON workflow_candidates(candidate_id)",
    "CREATE INDEX IF NOT EXISTS idx_workflow_candidates_confidence   ON workflow_candidates(confidence)",
    "CREATE INDEX IF NOT EXISTS idx_workflow_candidates_status       ON workflow_candidates(status)",
]

# ── blueprints ────────────────────────────────────────────────────────────────

BLUEPRINTS_TABLE = """
CREATE TABLE IF NOT EXISTS blueprints (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    blueprint_id  TEXT    UNIQUE NOT NULL,
    name          TEXT    NOT NULL,
    version       INTEGER NOT NULL,
    status        TEXT    NOT NULL,
    trigger_json  TEXT    NOT NULL,
    actions_json  TEXT    NOT NULL,
    rollback_json TEXT,
    confidence    REAL,
    metadata_json TEXT,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
)
"""

BLUEPRINTS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_blueprints_blueprint_id ON blueprints(blueprint_id)",
    "CREATE INDEX IF NOT EXISTS idx_blueprints_status       ON blueprints(status)",
    "CREATE INDEX IF NOT EXISTS idx_blueprints_name         ON blueprints(name)",
]

# ── audit_logs ────────────────────────────────────────────────────────────────

AUDIT_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id      TEXT    UNIQUE NOT NULL,
    timestamp     TEXT    NOT NULL,
    actor         TEXT    NOT NULL,
    action        TEXT    NOT NULL,
    resource_type TEXT,
    resource_id   TEXT,
    details_json  TEXT,
    created_at    TEXT    NOT NULL
)
"""

AUDIT_LOGS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_audit_id      ON audit_logs(audit_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp     ON audit_logs(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_action        ON audit_logs(action)",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_resource      ON audit_logs(resource_type, resource_id)",
]

# ── rejection_history ─────────────────────────────────────────────────────────

REJECTION_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS rejection_history (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    rejection_id     TEXT    UNIQUE NOT NULL,
    workflow_id      TEXT    NOT NULL,
    blueprint_id     TEXT    NOT NULL DEFAULT '',
    file_path        TEXT    NOT NULL,
    file_name        TEXT    NOT NULL,
    rejection_reason TEXT    NOT NULL DEFAULT '',
    rejection_type   TEXT    NOT NULL DEFAULT 'unknown',
    context_json     TEXT    NOT NULL DEFAULT '[]',
    rejected_at      TEXT    NOT NULL,
    created_at       TEXT    NOT NULL
)
"""

REJECTION_HISTORY_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_rejection_history_rejection_id  ON rejection_history(rejection_id)",
    "CREATE INDEX IF NOT EXISTS idx_rejection_history_workflow_id   ON rejection_history(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_rejection_history_file_name     ON rejection_history(file_name)",
    "CREATE INDEX IF NOT EXISTS idx_rejection_history_rejected_at   ON rejection_history(rejected_at)",
]

# ── exception_rules ───────────────────────────────────────────────────────────

EXCEPTION_RULES_TABLE = """
CREATE TABLE IF NOT EXISTS exception_rules (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id          TEXT    UNIQUE NOT NULL,
    workflow_id      TEXT    NOT NULL DEFAULT '',
    pattern          TEXT    NOT NULL,
    rule_type        TEXT    NOT NULL,
    match_strategy   TEXT    NOT NULL,
    confidence       REAL    NOT NULL,
    rejection_count  INTEGER NOT NULL DEFAULT 1,
    rationale        TEXT    NOT NULL DEFAULT '',
    is_active        INTEGER NOT NULL DEFAULT 1,
    last_rejection_at TEXT   NOT NULL,
    created_at       TEXT    NOT NULL,
    updated_at       TEXT    NOT NULL,
    UNIQUE(workflow_id, pattern, rule_type)
)
"""

EXCEPTION_RULES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_exception_rules_rule_id     ON exception_rules(rule_id)",
    "CREATE INDEX IF NOT EXISTS idx_exception_rules_workflow_id ON exception_rules(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_exception_rules_pattern     ON exception_rules(pattern)",
    "CREATE INDEX IF NOT EXISTS idx_exception_rules_is_active   ON exception_rules(is_active)",
]

# BuildNext plugin DDL lives in ghostflow/plugins/buildnext/storage/schemas.py
# and is imported by migration 003_buildnext_tables in migrations.py.

# ── workflow_definitions ──────────────────────────────────────────────────────

WORKFLOW_DEFINITIONS_TABLE = """
CREATE TABLE IF NOT EXISTS workflow_definitions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id         TEXT    UNIQUE NOT NULL,
    name                TEXT    NOT NULL,
    description         TEXT    NOT NULL DEFAULT '',
    version             INTEGER NOT NULL DEFAULT 1,
    steps_json          TEXT    NOT NULL DEFAULT '[]',
    edges_json          TEXT    NOT NULL DEFAULT '[]',
    input_schema_json   TEXT    NOT NULL DEFAULT '{}',
    output_schema_json  TEXT    NOT NULL DEFAULT '{}',
    tags_json           TEXT    NOT NULL DEFAULT '[]',
    is_template         INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT    NOT NULL,
    updated_at          TEXT    NOT NULL
)
"""

WORKFLOW_DEFINITIONS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_wf_def_workflow_id  ON workflow_definitions(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_wf_def_name         ON workflow_definitions(name)",
    "CREATE INDEX IF NOT EXISTS idx_wf_def_is_template  ON workflow_definitions(is_template)",
]

# ── workflow_executions ───────────────────────────────────────────────────────

WORKFLOW_EXECUTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS workflow_executions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id    TEXT    UNIQUE NOT NULL,
    workflow_id     TEXT    NOT NULL,
    workflow_name   TEXT    NOT NULL,
    status          TEXT    NOT NULL,
    input_json      TEXT    NOT NULL DEFAULT '{}',
    output_json     TEXT    NOT NULL DEFAULT '{}',
    error           TEXT,
    steps_json      TEXT    NOT NULL DEFAULT '[]',
    started_at      TEXT    NOT NULL,
    completed_at    TEXT,
    duration_ms     REAL,
    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions(workflow_id)
)
"""

WORKFLOW_EXECUTIONS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_wf_exec_execution_id ON workflow_executions(execution_id)",
    "CREATE INDEX IF NOT EXISTS idx_wf_exec_workflow_id  ON workflow_executions(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_wf_exec_status       ON workflow_executions(status)",
    "CREATE INDEX IF NOT EXISTS idx_wf_exec_started_at   ON workflow_executions(started_at)",
]

# ── persisted_policies ────────────────────────────────────────────────────────

PERSISTED_POLICIES_TABLE = """
CREATE TABLE IF NOT EXISTS persisted_policies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id       TEXT    UNIQUE NOT NULL,
    name            TEXT    NOT NULL,
    description     TEXT    NOT NULL DEFAULT '',
    effect          TEXT    NOT NULL,
    principals_json TEXT    NOT NULL DEFAULT '[]',
    permissions_json TEXT   NOT NULL DEFAULT '[]',
    resources_json  TEXT    NOT NULL DEFAULT '["*"]',
    conditions_json TEXT    NOT NULL DEFAULT '{}',
    priority        INTEGER NOT NULL DEFAULT 0,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
)
"""

PERSISTED_POLICIES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_pp_policy_id  ON persisted_policies(policy_id)",
    "CREATE INDEX IF NOT EXISTS idx_pp_effect      ON persisted_policies(effect)",
    "CREATE INDEX IF NOT EXISTS idx_pp_is_active   ON persisted_policies(is_active)",
]

# ── agent_executions ──────────────────────────────────────────────────────────

AGENT_EXECUTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS agent_executions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id    TEXT    UNIQUE NOT NULL,
    agent_id        TEXT    NOT NULL,
    agent_name      TEXT    NOT NULL,
    status          TEXT    NOT NULL,
    context_json    TEXT    NOT NULL DEFAULT '{}',
    output_json     TEXT    NOT NULL DEFAULT '{}',
    error           TEXT,
    duration_ms     REAL,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    started_at      TEXT    NOT NULL,
    completed_at    TEXT
)
"""

AGENT_EXECUTIONS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_ae_execution_id ON agent_executions(execution_id)",
    "CREATE INDEX IF NOT EXISTS idx_ae_agent_id     ON agent_executions(agent_id)",
    "CREATE INDEX IF NOT EXISTS idx_ae_status       ON agent_executions(status)",
    "CREATE INDEX IF NOT EXISTS idx_ae_started_at   ON agent_executions(started_at)",
]

# ── plugins ──────────────────────────────────────────────────────────────────

PLUGINS_TABLE = """
CREATE TABLE IF NOT EXISTS plugins (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_id     TEXT    UNIQUE NOT NULL,
    name          TEXT    NOT NULL,
    version       TEXT    NOT NULL DEFAULT '0.1.0',
    enabled       INTEGER NOT NULL DEFAULT 1,
    status        TEXT    NOT NULL DEFAULT 'registered',
    manifest_json TEXT    NOT NULL DEFAULT '{}',
    metadata_json TEXT    NOT NULL DEFAULT '{}',
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
)
"""

PLUGINS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_plugins_plugin_id ON plugins(plugin_id)",
    "CREATE INDEX IF NOT EXISTS idx_plugins_enabled   ON plugins(enabled)",
    "CREATE INDEX IF NOT EXISTS idx_plugins_status    ON plugins(status)",
]

# ── agents ───────────────────────────────────────────────────────────────────

AGENTS_TABLE = """
CREATE TABLE IF NOT EXISTS agents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id      TEXT    UNIQUE NOT NULL,
    plugin_id     TEXT,
    name          TEXT    NOT NULL,
    version       TEXT    NOT NULL DEFAULT '0.1.0',
    description   TEXT    NOT NULL DEFAULT '',
    tags_json     TEXT    NOT NULL DEFAULT '[]',
    metadata_json TEXT    NOT NULL DEFAULT '{}',
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
)
"""

AGENTS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_agents_agent_id  ON agents(agent_id)",
    "CREATE INDEX IF NOT EXISTS idx_agents_plugin_id ON agents(plugin_id)",
    "CREATE INDEX IF NOT EXISTS idx_agents_name      ON agents(name)",
]

# ── metrics ──────────────────────────────────────────────────────────────────

METRICS_TABLE = """
CREATE TABLE IF NOT EXISTS metrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_id       TEXT    UNIQUE NOT NULL,
    entity_type     TEXT    NOT NULL,
    entity_id       TEXT    NOT NULL,
    metric_name     TEXT    NOT NULL,
    metric_value    REAL    NOT NULL,
    dimensions_json TEXT    NOT NULL DEFAULT '{}',
    recorded_at     TEXT    NOT NULL
)
"""

METRICS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_metrics_metric_id   ON metrics(metric_id)",
    "CREATE INDEX IF NOT EXISTS idx_metrics_entity      ON metrics(entity_type, entity_id)",
    "CREATE INDEX IF NOT EXISTS idx_metrics_name        ON metrics(metric_name)",
    "CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at ON metrics(recorded_at)",
]
