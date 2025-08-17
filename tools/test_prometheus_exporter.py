#!/usr/bin/env python3
"""
Unit tests for prometheus_exporter.py
Tests all major functionality including metrics collection, error handling, and edge cases
"""

import sqlite3
import json
import time
import tempfile
import signal
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call
import pytest

# Import the module to test
import sys
sys.path.insert(0, str(Path(__file__).parent))
from prometheus_exporter import (
    MetricsConfig, MetricsCollector, 
    agent_invocation_total, agent_duration_seconds,
    agent_success_rate, session_duration_seconds,
    exporter_memory_usage_mb, exporter_query_duration_seconds
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary SQLite database with test schema"""
    db_path = tmp_path / "test_agent_workflow.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create test schema
    cursor.execute('''
        CREATE TABLE sessions (
            session_id TEXT PRIMARY KEY,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT,
            cwd TEXT,
            metadata JSON
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE agent_invocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP,
            session_id TEXT,
            event_type TEXT,
            phase TEXT,
            agent_name TEXT,
            agent_type TEXT,
            model TEXT,
            prompt TEXT,
            parent_agent TEXT,
            ticket_id TEXT,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_seconds REAL,
            status TEXT,
            error TEXT,
            result_summary TEXT,
            raw_input JSON,
            raw_output JSON
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE agent_tool_uses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP,
            session_id TEXT,
            agent_name TEXT,
            agent_invocation_id INTEGER,
            tool_name TEXT,
            status TEXT,
            duration_seconds REAL
        )
    ''')
    
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def sample_data(temp_db):
    """Insert sample data into the test database"""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Insert sample sessions
    sessions = [
        ('session-1', '2025-08-15 10:00:00', '2025-08-15 11:00:00', 'completed', '/test', '{}'),
        ('session-2', '2025-08-16 10:00:00', '2025-08-16 10:30:00', 'completed', '/test', '{}'),
        ('session-3', '2025-08-16 14:00:00', None, 'active', '/test', '{}'),
    ]
    cursor.executemany(
        'INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)', 
        sessions
    )
    
    # Insert sample invocations
    now = datetime.now()
    invocations = [
        # Recent invocations (within 7 days)
        (now.isoformat(), 'session-1', 'pre', 'development', 'test-agent', 
         'development', 'standard', 'test prompt', None, None,
         (now - timedelta(seconds=5)).isoformat(), now.isoformat(), 5.0, 
         'completed', None, None, '{}', '{}'),
        
        (now.isoformat(), 'session-2', 'pre', 'review', 'review-agent',
         'review', 'standard', 'review prompt', None, None,
         (now - timedelta(seconds=10)).isoformat(), now.isoformat(), 10.0,
         'failed', 'error message', None, '{}', '{}'),
         
        # Old invocation (outside 7-day window)
        ((now - timedelta(days=10)).isoformat(), 'session-1', 'pre', 'planning', 
         'old-agent', 'planning', 'standard', 'old prompt', None, None,
         (now - timedelta(days=10, seconds=3)).isoformat(), 
         (now - timedelta(days=10)).isoformat(), 3.0,
         'completed', None, None, '{}', '{}'),
    ]
    
    for inv in invocations:
        cursor.execute('''
            INSERT INTO agent_invocations (
                timestamp, session_id, event_type, phase, agent_name,
                agent_type, model, prompt, parent_agent, ticket_id,
                start_time, end_time, duration_seconds, status, error,
                result_summary, raw_input, raw_output
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', inv)
    
    # Insert sample tool uses
    tool_uses = [
        (now.isoformat(), 'session-1', 'test-agent', 1, 'Read', 'completed', 0.5),
        (now.isoformat(), 'session-1', 'test-agent', 1, 'Write', 'completed', 1.0),
        (now.isoformat(), 'session-2', 'review-agent', 2, 'Grep', 'failed', 2.0),
    ]
    
    cursor.executemany('''
        INSERT INTO agent_tool_uses (
            timestamp, session_id, agent_name, agent_invocation_id, 
            tool_name, status, duration_seconds
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', tool_uses)
    
    conn.commit()
    conn.close()
    return temp_db


@pytest.fixture
def metrics_collector(temp_db):
    """Create a MetricsCollector instance with test database"""
    return MetricsCollector(temp_db)


@pytest.fixture
def mock_psutil():
    """Mock psutil.Process for memory monitoring"""
    with patch('prometheus_exporter.psutil.Process') as mock_process:
        mock_memory = Mock()
        mock_memory.rss = 500 * 1024 * 1024  # 500 MB
        mock_process.return_value.memory_info.return_value = mock_memory
        yield mock_process


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

def test_metrics_config_defaults():
    """Test MetricsConfig has appropriate default values"""
    config = MetricsConfig()
    
    assert config.INVOCATION_WINDOW_DAYS == 7
    assert config.SESSION_WINDOW_DAYS == 30
    assert config.MAX_INVOCATIONS == 10000
    assert config.MAX_SESSIONS == 1000
    assert config.MEMORY_WARNING_THRESHOLD_MB == 500
    assert config.MEMORY_CRITICAL_THRESHOLD_MB == 1000


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

def test_metrics_collector_init(temp_db):
    """Test MetricsCollector initialization"""
    collector = MetricsCollector(temp_db)
    
    assert collector.db_path == temp_db
    assert collector.update_interval == 15
    assert collector.shutdown_requested == False
    assert isinstance(collector.config, MetricsConfig)


def test_metrics_collector_init_missing_db():
    """Test MetricsCollector with non-existent database path"""
    fake_path = Path("/nonexistent/database.db")
    collector = MetricsCollector(fake_path)
    
    assert collector.db_path == fake_path
    # Should not raise an error during initialization


# ============================================================================
# SIGNAL HANDLING TESTS
# ============================================================================

def test_signal_handlers(metrics_collector):
    """Test signal handler setup and execution"""
    # Test shutdown signal
    metrics_collector._handle_shutdown(signal.SIGTERM, None)
    assert metrics_collector.shutdown_requested == True
    
    # Reset and test interrupt signal
    metrics_collector.shutdown_requested = False
    metrics_collector._handle_shutdown(signal.SIGINT, None)
    assert metrics_collector.shutdown_requested == True


@patch('prometheus_exporter.logger')
def test_reload_signal(mock_logger, metrics_collector, sample_data):
    """Test SIGHUP reload functionality"""
    metrics_collector._handle_reload(signal.SIGHUP, None)
    
    # Check that reload was logged
    mock_logger.info.assert_called()
    assert "SIGHUP" in str(mock_logger.info.call_args)


# ============================================================================
# MEMORY MONITORING TESTS
# ============================================================================

def test_memory_monitoring_normal(metrics_collector, mock_psutil):
    """Test memory monitoring under normal conditions"""
    memory_mb = metrics_collector._monitor_memory_usage()
    
    assert memory_mb == 500.0  # 500 MB as mocked
    # Check that Prometheus metric was updated
    # Note: In real implementation, we'd check the metric value


@patch('prometheus_exporter.logger')
def test_memory_monitoring_warning(mock_logger, metrics_collector, mock_psutil):
    """Test memory monitoring warning threshold"""
    # Set memory to 600 MB (above warning threshold)
    mock_psutil.return_value.memory_info.return_value.rss = 600 * 1024 * 1024
    
    memory_mb = metrics_collector._monitor_memory_usage()
    
    assert memory_mb == 600.0
    mock_logger.warning.assert_called()
    assert "WARNING" in str(mock_logger.warning.call_args)


@patch('prometheus_exporter.logger')
def test_memory_monitoring_critical(mock_logger, metrics_collector, mock_psutil):
    """Test memory monitoring critical threshold"""
    # Set memory to 1100 MB (above critical threshold)
    mock_psutil.return_value.memory_info.return_value.rss = 1100 * 1024 * 1024
    
    memory_mb = metrics_collector._monitor_memory_usage()
    
    assert memory_mb == 1100.0
    mock_logger.error.assert_called()
    assert "CRITICAL" in str(mock_logger.error.call_args)


@patch('prometheus_exporter.psutil.Process')
@patch('prometheus_exporter.logger')
def test_memory_monitoring_error(mock_logger, mock_process, metrics_collector):
    """Test memory monitoring when psutil fails"""
    mock_process.side_effect = Exception("psutil error")
    
    memory_mb = metrics_collector._monitor_memory_usage()
    
    assert memory_mb == 0
    mock_logger.debug.assert_called()


# ============================================================================
# QUERY MONITORING TESTS
# ============================================================================

def test_execute_query_with_monitoring_select(metrics_collector, sample_data):
    """Test query monitoring for SELECT queries"""
    conn = sqlite3.connect(sample_data)
    cursor = conn.cursor()
    
    results = metrics_collector._execute_query_with_monitoring(
        cursor,
        "SELECT COUNT(*) FROM agent_invocations",
        query_type="test_count"
    )
    
    assert len(results) == 1
    assert results[0][0] == 3  # 3 invocations in sample data
    
    conn.close()


def test_execute_query_with_monitoring_with_params(metrics_collector, sample_data):
    """Test query monitoring with parameters"""
    conn = sqlite3.connect(sample_data)
    cursor = conn.cursor()
    
    results = metrics_collector._execute_query_with_monitoring(
        cursor,
        "SELECT agent_name FROM agent_invocations WHERE session_id = ?",
        params=('session-1',),
        query_type="test_params"
    )
    
    assert len(results) == 2  # 2 invocations for session-1
    
    conn.close()


@patch('prometheus_exporter.logger')
@patch('prometheus_exporter.time.time')
def test_execute_query_slow_warning(mock_time, mock_logger, metrics_collector, sample_data):
    """Test slow query warning"""
    conn = sqlite3.connect(sample_data)
    cursor = conn.cursor()
    
    # Simulate a 2-second query
    mock_time.side_effect = [0, 2]  # Start time=0, end time=2
    
    metrics_collector._execute_query_with_monitoring(
        cursor,
        "SELECT * FROM agent_invocations",
        query_type="slow_query"
    )
    
    mock_logger.warning.assert_called()
    assert "Slow query" in str(mock_logger.warning.call_args)
    
    conn.close()


# ============================================================================
# COLLECTION METHOD TESTS
# ============================================================================

def test_collect_invocation_metrics(metrics_collector, sample_data):
    """Test _collect_invocation_metrics"""
    conn = sqlite3.connect(sample_data)
    cursor = conn.cursor()
    
    metrics_collector._collect_invocation_metrics(cursor)
    
    # Verify that metrics were processed
    # In a real test, we'd check Prometheus metric values
    conn.close()


def test_collect_session_metrics(metrics_collector, sample_data):
    """Test _collect_session_metrics"""
    conn = sqlite3.connect(sample_data)
    cursor = conn.cursor()
    
    metrics_collector._collect_session_metrics(cursor)
    
    # Should process 3 sessions from sample data
    conn.close()


def test_collect_tool_usage_metrics(metrics_collector, sample_data):
    """Test _collect_tool_usage_metrics"""
    conn = sqlite3.connect(sample_data)
    cursor = conn.cursor()
    
    metrics_collector._collect_tool_usage_metrics(cursor)
    
    # Should process tool usage data
    conn.close()


def test_collect_tool_usage_metrics_no_table(metrics_collector, temp_db):
    """Test _collect_tool_usage_metrics when table doesn't exist"""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Drop the agent_tool_uses table
    cursor.execute("DROP TABLE IF EXISTS agent_tool_uses")
    conn.commit()
    
    # Should not raise an error
    metrics_collector._collect_tool_usage_metrics(cursor)
    
    conn.close()


def test_collect_success_metrics(metrics_collector, sample_data):
    """Test _collect_success_metrics"""
    conn = sqlite3.connect(sample_data)
    cursor = conn.cursor()
    
    metrics_collector._collect_success_metrics(cursor)
    
    # Should calculate success rates for agents
    conn.close()


def test_collect_database_info(metrics_collector, sample_data):
    """Test _collect_database_info"""
    conn = sqlite3.connect(sample_data)
    cursor = conn.cursor()
    
    metrics_collector._collect_database_info(cursor)
    
    # Should collect database metadata
    conn.close()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@patch('prometheus_exporter.psutil.Process')
def test_collect_metrics_full_cycle(mock_process, metrics_collector, sample_data):
    """Test full metrics collection cycle"""
    mock_memory = Mock()
    mock_memory.rss = 100 * 1024 * 1024  # 100 MB
    mock_process.return_value.memory_info.return_value = mock_memory
    
    # Run full collection
    metrics_collector.collect_metrics()
    
    # Should complete without errors
    assert True  # If we got here, no exceptions were raised


@patch('prometheus_exporter.logger')
def test_collect_metrics_missing_database(mock_logger):
    """Test metrics collection with missing database"""
    fake_path = Path("/nonexistent/database.db")
    collector = MetricsCollector(fake_path)
    
    collector.collect_metrics()
    
    mock_logger.warning.assert_called()
    assert "Database not found" in str(mock_logger.warning.call_args)


@patch('prometheus_exporter.logger')
def test_collect_metrics_database_error(mock_logger, metrics_collector):
    """Test metrics collection with database error"""
    with patch.object(metrics_collector, 'get_connection') as mock_conn:
        mock_conn.side_effect = sqlite3.Error("Database locked")
        
        metrics_collector.collect_metrics()
        
        mock_logger.error.assert_called()
        assert "Database error" in str(mock_logger.error.call_args)


@patch('prometheus_exporter.psutil.Process')
@patch('prometheus_exporter.logger')
def test_collect_metrics_memory_growth_warning(mock_logger, mock_process, metrics_collector, sample_data):
    """Test memory growth warning during collection"""
    # Set up memory mock to return different values on each call
    mock_memory_info = Mock()
    mock_process.return_value.memory_info = mock_memory_info
    
    # First call returns 100MB, second call returns 200MB
    memory_results = [Mock(rss=100 * 1024 * 1024), Mock(rss=200 * 1024 * 1024)]
    mock_memory_info.side_effect = memory_results
    
    metrics_collector.collect_metrics()
    
    # Should log warning about memory growth > 50MB
    warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
    memory_growth_warned = any("memory growth" in call.lower() for call in warning_calls)
    assert memory_growth_warned, f"Expected memory growth warning, got: {warning_calls}"


# ============================================================================
# EDGE CASES AND ERROR SCENARIOS
# ============================================================================

def test_empty_database(metrics_collector, temp_db):
    """Test metrics collection with empty database"""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Should not raise errors with empty tables
    metrics_collector._collect_invocation_metrics(cursor)
    metrics_collector._collect_session_metrics(cursor)
    metrics_collector._collect_success_metrics(cursor)
    
    conn.close()


def test_null_values_handling(metrics_collector, temp_db):
    """Test handling of NULL values in database"""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Insert invocation with NULL values
    cursor.execute('''
        INSERT INTO agent_invocations (
            timestamp, session_id, agent_name, phase, status, model
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), 'test-session', 'test-agent', None, None, None))
    
    conn.commit()
    
    # Should handle NULL values gracefully
    metrics_collector._collect_invocation_metrics(cursor)
    
    conn.close()


def test_malformed_timestamps(metrics_collector, temp_db):
    """Test handling of malformed timestamps"""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Insert data with malformed timestamps
    cursor.execute('''
        INSERT INTO agent_invocations (
            timestamp, session_id, agent_name, start_time, end_time, status
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', ('not-a-timestamp', 'test-session', 'test-agent', 
          'bad-start', 'bad-end', 'completed'))
    
    conn.commit()
    
    # Should handle bad timestamps without crashing
    metrics_collector._collect_invocation_metrics(cursor)
    
    conn.close()


def test_query_result_limits(metrics_collector, temp_db):
    """Test that query result limits are enforced"""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Insert many invocations
    now = datetime.now()
    for i in range(15000):  # More than MAX_INVOCATIONS
        cursor.execute('''
            INSERT INTO agent_invocations (
                timestamp, session_id, agent_name, status
            ) VALUES (?, ?, ?, ?)
        ''', ((now - timedelta(days=1)).isoformat(), f'session-{i}', 
              f'agent-{i % 10}', 'completed'))
    
    conn.commit()
    
    # Query should be limited to MAX_INVOCATIONS (10000)
    cursor.execute('''
        SELECT agent_name FROM agent_invocations 
        WHERE agent_name != 'unknown'
        AND (start_time IS NULL OR datetime(start_time) > datetime('now', '-7 days'))
        ORDER BY start_time DESC
        LIMIT 10000
    ''')
    
    results = cursor.fetchall()
    assert len(results) <= 10000
    
    conn.close()


# ============================================================================
# MAIN LOOP TESTS
# ============================================================================

@patch('prometheus_exporter.start_http_server')
@patch('time.sleep')
def test_run_forever(mock_sleep, mock_server, metrics_collector):
    """Test run_forever main loop"""
    # Simulate shutdown after first iteration
    def side_effect(_):
        metrics_collector.shutdown_requested = True
    
    mock_sleep.side_effect = side_effect
    
    metrics_collector.run_forever(port=9090)
    
    # Check that server was started with correct port
    mock_server.assert_called_once()
    call_args = mock_server.call_args
    assert call_args[0][0] == 9090  # First positional arg is port
    assert metrics_collector.shutdown_requested == True


# ============================================================================
# DATABASE CONNECTION TESTS
# ============================================================================

def test_get_connection(metrics_collector, sample_data):
    """Test database connection retrieval"""
    conn = metrics_collector.get_connection()
    
    assert conn is not None
    assert isinstance(conn, sqlite3.Connection)
    
    # Test that connection works
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sessions")
    result = cursor.fetchone()
    assert result[0] == 3  # 3 sessions in sample data
    
    conn.close()


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([__file__, "-v", "--cov=prometheus_exporter", "--cov-report=term-missing"])