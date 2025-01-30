-- エージェント設定テーブル
CREATE TABLE IF NOT EXISTS agent_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    model_path TEXT,
    embedding_dim INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- アクション履歴テーブル
CREATE TABLE IF NOT EXISTS action_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER,
    action_type TEXT NOT NULL,
    action_data TEXT,
    embedding BLOB,  -- ベクトル化されたアクション
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (agent_id) REFERENCES agent_config(id)
);

-- 学習データテーブル
CREATE TABLE IF NOT EXISTS training_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER,
    input_data TEXT NOT NULL,
    output_data TEXT NOT NULL,
    input_embedding BLOB,  -- 入力のベクトル表現
    output_embedding BLOB,  -- 出力のベクトル表現
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agent_config(id)
);

-- システムメトリクステーブル
CREATE TABLE IF NOT EXISTS system_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER,
    cpu_usage REAL,
    memory_usage REAL,
    gpu_usage REAL,
    latency REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agent_config(id)
);

-- エージェント状態テーブル
CREATE TABLE IF NOT EXISTS agent_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER,
    current_task TEXT,
    state_data TEXT,  -- JSON形式の状態データ
    attention_weights BLOB,  -- 自己注意の重み
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agent_config(id)
);

-- メトリクステーブル
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value TEXT NOT NULL,
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_type ON metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);

-- ベクターストアテーブル
CREATE TABLE IF NOT EXISTS vector_store (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    embedding BLOB NOT NULL,
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_vector_store_created ON vector_store(created_at);

-- バックアップメタデータテーブル
CREATE TABLE IF NOT EXISTS backup_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_path TEXT NOT NULL,
    backup_time DATETIME NOT NULL,
    metrics_count INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_backup_time ON backup_metadata(backup_time);

-- 監査ログテーブル
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id INTEGER,
    old_value TEXT,
    new_value TEXT,
    user_id TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action_type);

-- トリガー: メトリクス監査
CREATE TRIGGER IF NOT EXISTS audit_metrics_insert AFTER INSERT ON metrics
BEGIN
    INSERT INTO audit_log (action_type, table_name, record_id, new_value)
    VALUES ('INSERT', 'metrics', NEW.id, json_object(
        'metric_type', NEW.metric_type,
        'metric_name', NEW.metric_name,
        'metric_value', NEW.metric_value
    ));
END;

CREATE TRIGGER IF NOT EXISTS audit_metrics_update AFTER UPDATE ON metrics
BEGIN
    INSERT INTO audit_log (action_type, table_name, record_id, old_value, new_value)
    VALUES ('UPDATE', 'metrics', NEW.id, json_object(
        'metric_type', OLD.metric_type,
        'metric_name', OLD.metric_name,
        'metric_value', OLD.metric_value
    ), json_object(
        'metric_type', NEW.metric_type,
        'metric_name', NEW.metric_name,
        'metric_value', NEW.metric_value
    ));
END;

CREATE TRIGGER IF NOT EXISTS audit_metrics_delete AFTER DELETE ON metrics
BEGIN
    INSERT INTO audit_log (action_type, table_name, record_id, old_value)
    VALUES ('DELETE', 'metrics', OLD.id, json_object(
        'metric_type', OLD.metric_type,
        'metric_name', OLD.metric_name,
        'metric_value', OLD.metric_value
    ));
END;

-- インデックスの作成
CREATE INDEX IF NOT EXISTS idx_action_history_agent ON action_history(agent_id);
CREATE INDEX IF NOT EXISTS idx_action_history_timestamp ON action_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_training_data_agent ON training_data(agent_id);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_agent_state_agent ON agent_state(agent_id);

-- メトリクステーブルのインデックス
CREATE INDEX IF NOT EXISTS idx_metrics_type_timestamp ON metrics(metric_type, timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp ON metrics(metric_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_value ON metrics(metric_value);

-- ベクターストアのインデックス
CREATE INDEX IF NOT EXISTS idx_vector_store_embedding ON vector_store(embedding);
CREATE INDEX IF NOT EXISTS idx_vector_store_metadata ON vector_store(metadata);

-- バックアップメタデータのインデックス
CREATE INDEX IF NOT EXISTS idx_backup_status ON backup_metadata(status);
CREATE INDEX IF NOT EXISTS idx_backup_metrics_count ON backup_metadata(metrics_count);

-- 監査ログのインデックス
CREATE INDEX IF NOT EXISTS idx_audit_table_record ON audit_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);

-- パフォーマンス最適化のためのVIEW
CREATE VIEW IF NOT EXISTS v_recent_metrics AS
SELECT *
FROM metrics
WHERE timestamp >= datetime('now', '-1 hour');

CREATE VIEW IF NOT EXISTS v_error_metrics AS
SELECT *
FROM metrics
WHERE metric_type = 'error'
ORDER BY timestamp DESC;

CREATE VIEW IF NOT EXISTS v_performance_metrics AS
SELECT 
    strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
    metric_type,
    metric_name,
    AVG(CAST(metric_value AS FLOAT)) as avg_value,
    MIN(CAST(metric_value AS FLOAT)) as min_value,
    MAX(CAST(metric_value AS FLOAT)) as max_value,
    COUNT(*) as sample_count
FROM metrics
WHERE metric_type IN ('cpu', 'memory', 'gpu', 'latency')
GROUP BY hour, metric_type, metric_name; 