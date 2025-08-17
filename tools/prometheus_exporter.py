#!/usr/bin/env python3
"""
Prometheus Exporter for Agent Workflow Metrics
Exposes SQLite database metrics in Prometheus format for Grafana visualization
"""

import sqlite3
import time
import argparse
import logging
import signal
import sys
import psutil
from pathlib import Path
from datetime import datetime, timedelta
from prometheus_client import start_http_server, Counter, Histogram, Gauge, Info
from prometheus_client.core import CollectorRegistry
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Setup paths
TOOLS_DIR = Path(__file__).parent
PROJECT_DIR = TOOLS_DIR.parent
LOGS_DIR = PROJECT_DIR / "logs"
DB_PATH = LOGS_DIR / "agent_workflow.db"

# Create a custom registry to avoid conflicts
registry = CollectorRegistry()

# Configuration for query limits (prevent memory exhaustion)
class MetricsConfig:
    # Time windows for data collection
    INVOCATION_WINDOW_DAYS = 7
    SESSION_WINDOW_DAYS = 30
    TOOL_USAGE_WINDOW_DAYS = 7
    
    # Result limits
    MAX_INVOCATIONS = 10000
    MAX_SESSIONS = 1000
    MAX_TOOL_USAGE_RECORDS = 1000
    MAX_DURATION_RECORDS = 5000
    MAX_AGENTS = 100
    MAX_TOOL_COMBINATIONS = 500
    
    # Memory monitoring
    MEMORY_WARNING_THRESHOLD_MB = 500
    MEMORY_CRITICAL_THRESHOLD_MB = 1000

# Define Prometheus metrics

# Agent-specific metrics
agent_invocation_total = Gauge(
    'agent_invocation_total',
    'Total number of agent invocations',
    ['agent_name', 'phase', 'status', 'model'],
    registry=registry
)

agent_duration_seconds = Histogram(
    'agent_duration_seconds',
    'Agent execution duration in seconds',
    ['agent_name', 'phase', 'model'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1200, 3600],
    registry=registry
)

agent_last_execution_timestamp = Gauge(
    'agent_last_execution_timestamp',
    'Timestamp of last agent execution',
    ['agent_name'],
    registry=registry
)

session_duration_seconds = Histogram(
    'session_duration_seconds',
    'Session duration in seconds',
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400],
    registry=registry
)

active_sessions_count = Gauge(
    'active_sessions_count',
    'Number of currently active sessions',
    registry=registry
)

parallel_executions_current = Gauge(
    'parallel_executions_current',
    'Current number of parallel agent executions',
    registry=registry
)

agent_error_total = Counter(
    'agent_error_total',
    'Total number of agent errors',
    ['agent_name', 'phase'],
    registry=registry
)

phase_distribution_total = Gauge(
    'phase_distribution_total',
    'Distribution of agents across phases',
    ['phase'],
    registry=registry
)

agent_success_rate = Gauge(
    'agent_success_rate',
    'Success rate percentage for each agent',
    ['agent_name'],
    registry=registry
)

database_info = Info(
    'agent_workflow_database',
    'Information about the agent workflow database',
    registry=registry
)

total_agents_gauge = Gauge(
    'total_unique_agents',
    'Total number of unique agents in the system',
    registry=registry
)

total_sessions_gauge = Gauge(
    'total_sessions',
    'Total number of sessions logged',
    registry=registry
)

avg_agents_per_session = Gauge(
    'avg_agents_per_session',
    'Average number of agents invoked per session',
    registry=registry
)

# Session-specific metrics
session_agents_total = Gauge(
    'session_agents_total',
    'Total number of agents used in session',
    ['session_id'],
    registry=registry
)

session_phases_completed = Gauge(
    'session_phases_completed',
    'Number of distinct phases completed in session',
    ['session_id'],
    registry=registry
)

session_success_rate = Gauge(
    'session_success_rate',
    'Success rate percentage within session',
    ['session_id'],
    registry=registry
)

session_error_count = Gauge(
    'session_error_count',
    'Total errors in session',
    ['session_id'],
    registry=registry
)

session_total_agent_time = Gauge(
    'session_total_agent_time',
    'Sum of all agent execution times in session (seconds)',
    ['session_id'],
    registry=registry
)

session_idle_time = Gauge(
    'session_idle_time',
    'Time between agent invocations in session (seconds)',
    ['session_id'],
    registry=registry
)

session_efficiency_ratio = Gauge(
    'session_efficiency_ratio',
    'Ratio of agent execution time to total session time',
    ['session_id'],
    registry=registry
)

session_parallel_factor = Gauge(
    'session_parallel_factor',
    'Maximum parallel agents running in session',
    ['session_id'],
    registry=registry
)

session_start_timestamp = Gauge(
    'session_start_timestamp',
    'Unix timestamp when session started',
    ['session_id'],
    registry=registry
)

session_agent_diversity = Gauge(
    'session_agent_diversity',
    'Ratio of unique agents to total invocations in session',
    ['session_id'],
    registry=registry
)

session_duration_by_first_agent = Histogram(
    'session_duration_by_first_agent',
    'Session duration grouped by first agent invoked',
    ['first_agent'],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400],
    registry=registry
)

session_completion_status = Gauge(
    'session_completion_status',
    'Session completion status (0=failed, 1=partial, 2=complete)',
    ['session_id', 'status'],
    registry=registry
)

# Tool usage metrics
agent_tool_usage_total = Gauge(
    'agent_tool_usage_total',
    'Total tool uses by agent and tool',
    ['agent_name', 'tool_name'],
    registry=registry
)

agent_tool_duration_seconds = Histogram(
    'agent_tool_duration_seconds',
    'Tool execution duration by agent',
    ['agent_name', 'tool_name'],
    buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 120, 300],
    registry=registry
)

tools_per_agent_invocation = Gauge(
    'tools_per_agent_invocation',
    'Average number of tools used per agent invocation',
    ['agent_name'],
    registry=registry
)

agent_tool_diversity = Gauge(
    'agent_tool_diversity',
    'Unique tools used / total tool calls per agent',
    ['agent_name'],
    registry=registry
)

agent_tool_success_rate = Gauge(
    'agent_tool_success_rate',
    'Tool success rate by agent and tool',
    ['agent_name', 'tool_name'],
    registry=registry
)

agent_primary_tool = Info(
    'agent_primary_tool',
    'Most frequently used tool by each agent',
    registry=registry
)

# Memory usage metrics for monitoring query performance
exporter_memory_usage_mb = Gauge(
    'exporter_memory_usage_mb',
    'Memory usage of the prometheus exporter in MB',
    registry=registry
)

exporter_query_duration_seconds = Histogram(
    'exporter_query_duration_seconds',
    'Duration of database queries in seconds',
    ['query_type'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 30],
    registry=registry
)

exporter_query_result_count = Histogram(
    'exporter_query_result_count',
    'Number of rows returned by database queries',
    ['query_type'],
    buckets=[1, 10, 100, 500, 1000, 5000, 10000, 50000],
    registry=registry
)

class MetricsCollector:
    """Collects and exposes metrics from SQLite database"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.last_update = None
        self.update_interval = 15  # seconds
        self.shutdown_requested = False
        self.config = MetricsConfig()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, self._handle_reload)
    
    def _monitor_memory_usage(self):
        """Monitor and report memory usage"""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            exporter_memory_usage_mb.set(memory_mb)
            
            if memory_mb > self.config.MEMORY_CRITICAL_THRESHOLD_MB:
                logger.error(f"CRITICAL: Memory usage {memory_mb:.1f}MB exceeds threshold {self.config.MEMORY_CRITICAL_THRESHOLD_MB}MB")
            elif memory_mb > self.config.MEMORY_WARNING_THRESHOLD_MB:
                logger.warning(f"WARNING: Memory usage {memory_mb:.1f}MB exceeds threshold {self.config.MEMORY_WARNING_THRESHOLD_MB}MB")
            
            return memory_mb
        except Exception as e:
            logger.debug(f"Could not monitor memory usage: {e}")
            return 0
            
    def _execute_query_with_monitoring(self, cursor, query, params=None, query_type="unknown"):
        """Execute query with performance monitoring"""
        start_time = time.time()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                result_count = len(results)
                exporter_query_result_count.labels(query_type=query_type).observe(result_count)
                
                if result_count > 5000:
                    logger.warning(f"Large query result: {result_count} rows for {query_type}")
                    
                return results
            else:
                return cursor.fetchall()
                
        finally:
            duration = time.time() - start_time
            exporter_query_duration_seconds.labels(query_type=query_type).observe(duration)
            
            if duration > 1.0:
                logger.warning(f"Slow query: {duration:.2f}s for {query_type}")
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
    
    def _handle_reload(self, signum, frame):
        """Handle reload signal by forcing metrics update"""
        logger.info(f"Received SIGHUP, forcing metrics update...")
        try:
            self.collect_metrics()
            logger.info("Metrics updated successfully after SIGHUP")
        except Exception as e:
            logger.error(f"Failed to update metrics after SIGHUP: {e}")
        
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def collect_metrics(self):
        """Collect all metrics from database"""
        if not self.db_path.exists():
            logger.warning(f"Database not found at {self.db_path}")
            return
        
        # Monitor memory usage before collection
        initial_memory = self._monitor_memory_usage()
        
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Collect invocation metrics
            self._collect_invocation_metrics(cursor)
            
            # Collect session metrics
            self._collect_session_metrics(cursor)
            
            # Collect parallel execution metrics
            self._collect_parallel_metrics(cursor)
            
            # Collect success rate metrics
            self._collect_success_metrics(cursor)
            
            # Collect database info
            self._collect_database_info(cursor)
            
            # Collect tool usage metrics
            self._collect_tool_usage_metrics(cursor)
            
            conn.close()
            
            # Monitor memory usage after collection
            final_memory = self._monitor_memory_usage()
            memory_growth = final_memory - initial_memory
            
            if memory_growth > 50:  # MB
                logger.warning(f"High memory growth during collection: +{memory_growth:.1f}MB")
            
        except sqlite3.Error as e:
            logger.error(f"Database error while collecting metrics: {e}")
            if conn:
                conn.close()
        except Exception as e:
            logger.error(f"Unexpected error collecting metrics: {e}", exc_info=True)
            if conn:
                conn.close()
    
    def _collect_invocation_metrics(self, cursor):
        """Collect agent invocation metrics"""
        # Get recent invocations with timing (last 7 days to prevent memory exhaustion)
        cursor.execute('''
            SELECT agent_name, phase, status, model,
                   start_time, end_time,
                   (julianday(end_time) - julianday(start_time)) * 86400 as duration
            FROM agent_invocations
            WHERE agent_name != 'unknown'
            AND (start_time IS NULL OR datetime(start_time) > datetime('now', '-7 days'))
            ORDER BY start_time DESC
            LIMIT 10000
        ''')
        
        invocations = cursor.fetchall()
        
        # Count invocations by labels
        invocation_counts = defaultdict(int)
        phase_counts = defaultdict(int)
        
        for agent, phase, status, model, start, end, duration in invocations:
            # Default values for None
            phase = phase or 'unknown'
            status = status or 'unknown'
            model = model or 'unknown'
            
            # Count invocations
            key = (agent, phase, status, model)
            invocation_counts[key] += 1
            
            # Track phase distribution
            phase_counts[phase] += 1
            
            # Track duration if available
            if duration and duration > 0:
                agent_duration_seconds.labels(
                    agent_name=agent,
                    phase=phase,
                    model=model
                ).observe(duration)
            
            # Track last execution time
            if start:
                try:
                    timestamp = datetime.fromisoformat(start).timestamp()
                    agent_last_execution_timestamp.labels(agent_name=agent).set(timestamp)
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Could not parse timestamp '{start}': {e}")
            
            # Track errors
            if status in ['failed', 'error']:
                agent_error_total.labels(agent_name=agent, phase=phase).inc()
        
        # Set invocation counts
        for (agent, phase, status, model), count in invocation_counts.items():
            agent_invocation_total.labels(
                agent_name=agent,
                phase=phase,
                status=status,
                model=model
            ).set(count)
        
        # Update phase distribution
        for phase, count in phase_counts.items():
            phase_distribution_total.labels(phase=phase).set(count)
    
    def _collect_session_metrics(self, cursor):
        """Collect session-related metrics"""
        # Get recent session durations (last 30 days to prevent memory exhaustion)
        sessions = self._execute_query_with_monitoring(
            cursor,
            '''
            SELECT session_id, start_time, end_time,
                   (julianday(end_time) - julianday(start_time)) * 86400 as duration
            FROM sessions
            WHERE end_time IS NOT NULL
            AND (start_time IS NULL OR datetime(start_time) > datetime('now', '-30 days'))
            ORDER BY start_time DESC
            LIMIT 1000
            ''',
            query_type="sessions"
        )
        for session_id, start, end, duration in sessions:
            if duration and duration > 0:
                session_duration_seconds.observe(duration)
        
        # Count active sessions
        cursor.execute('''
            SELECT COUNT(*) FROM sessions
            WHERE end_time IS NULL OR status = 'active'
        ''')
        active_count = cursor.fetchone()[0]
        active_sessions_count.set(active_count)
        
        # Total sessions
        cursor.execute('SELECT COUNT(*) FROM sessions')
        total = cursor.fetchone()[0]
        total_sessions_gauge.set(total)
        
        # Average agents per session
        cursor.execute('''
            SELECT AVG(agent_count) FROM (
                SELECT session_id, COUNT(DISTINCT agent_name) as agent_count
                FROM agent_invocations
                WHERE agent_name != 'unknown'
                GROUP BY session_id
            )
        ''')
        avg = cursor.fetchone()[0]
        if avg:
            avg_agents_per_session.set(avg)
        
        # Collect detailed per-session metrics
        self._collect_detailed_session_metrics(cursor)
    
    def _collect_detailed_session_metrics(self, cursor):
        """Collect detailed metrics for each session"""
        # Get all sessions
        cursor.execute('''
            SELECT s.session_id, s.start_time, s.end_time, s.status
            FROM sessions s
            ORDER BY s.start_time DESC
            LIMIT 50
        ''')
        
        sessions = cursor.fetchall()
        
        for session_id, start_time, end_time, status in sessions:
            # Short session ID for labels (first 8 chars)
            short_id = session_id[:8] if session_id else 'unknown'
            
            # Session start timestamp
            if start_time:
                try:
                    timestamp = datetime.fromisoformat(start_time).timestamp()
                    session_start_timestamp.labels(session_id=short_id).set(timestamp)
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Could not parse session timestamp '{start_time}': {e}")
            
            # Get agent metrics for this session
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT agent_name) as unique_agents,
                    COUNT(*) as total_invocations,
                    COUNT(DISTINCT phase) as phases_completed,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN status IN ('failed', 'error') THEN 1 ELSE 0 END) as error_count,
                    SUM(CASE WHEN end_time IS NOT NULL AND start_time IS NOT NULL 
                        THEN (julianday(end_time) - julianday(start_time)) * 86400 
                        ELSE 0 END) as total_agent_time,
                    MIN(start_time) as first_start,
                    MAX(end_time) as last_end
                FROM agent_invocations
                WHERE session_id = ? AND agent_name != 'unknown'
            ''', (session_id,))
            
            result = cursor.fetchone()
            if result:
                (unique_agents, total_invocations, phases_completed, success_count, 
                 error_count, total_agent_time, first_start, last_end) = result
                
                # Set basic metrics
                if total_invocations > 0:
                    session_agents_total.labels(session_id=short_id).set(total_invocations)
                    session_phases_completed.labels(session_id=short_id).set(phases_completed or 0)
                    session_error_count.labels(session_id=short_id).set(error_count or 0)
                    
                    # Success rate
                    success_rate = (success_count / total_invocations * 100) if total_invocations > 0 else 0
                    session_success_rate.labels(session_id=short_id).set(success_rate)
                    
                    # Agent diversity
                    diversity = unique_agents / total_invocations if total_invocations > 0 else 0
                    session_agent_diversity.labels(session_id=short_id).set(diversity)
                    
                    # Total agent execution time
                    session_total_agent_time.labels(session_id=short_id).set(total_agent_time or 0)
                    
                    # Calculate efficiency if session is complete
                    if end_time and start_time:
                        try:
                            session_duration = (datetime.fromisoformat(end_time) - 
                                              datetime.fromisoformat(start_time)).total_seconds()
                            if session_duration > 0:
                                efficiency = (total_agent_time / session_duration) if total_agent_time else 0
                                session_efficiency_ratio.labels(session_id=short_id).set(efficiency)
                                
                                # Idle time
                                idle_time = session_duration - (total_agent_time or 0)
                                session_idle_time.labels(session_id=short_id).set(max(0, idle_time))
                        except (ValueError, AttributeError, TypeError) as e:
                            logger.debug(f"Could not calculate session efficiency for {short_id}: {e}")
                    
                    # Completion status (0=failed, 1=partial, 2=complete)
                    if status == 'completed' or success_rate > 90:
                        completion_status = 2
                    elif success_rate > 50:
                        completion_status = 1
                    else:
                        completion_status = 0
                    session_completion_status.labels(
                        session_id=short_id, 
                        status=['failed', 'partial', 'complete'][completion_status]
                    ).set(completion_status)
            
            # Get first agent for grouping
            cursor.execute('''
                SELECT agent_name 
                FROM agent_invocations 
                WHERE session_id = ? AND agent_name != 'unknown'
                ORDER BY timestamp 
                LIMIT 1
            ''', (session_id,))
            
            first_agent_result = cursor.fetchone()
            if first_agent_result and end_time and start_time:
                first_agent = first_agent_result[0]
                try:
                    duration = (datetime.fromisoformat(end_time) - 
                               datetime.fromisoformat(start_time)).total_seconds()
                    if duration > 0:
                        session_duration_by_first_agent.labels(first_agent=first_agent).observe(duration)
                except (ValueError, AttributeError, TypeError) as e:
                    logger.debug(f"Could not calculate duration for first agent {first_agent}: {e}")
            
            # Calculate max parallel factor
            cursor.execute('''
                SELECT MAX(parallel_count) FROM (
                    SELECT COUNT(*) as parallel_count
                    FROM agent_invocations a1
                    WHERE a1.session_id = ?
                    AND a1.start_time IS NOT NULL
                    AND EXISTS (
                        SELECT 1 FROM agent_invocations a2
                        WHERE a2.session_id = a1.session_id
                        AND a2.agent_name != a1.agent_name
                        AND a2.start_time <= a1.end_time
                        AND a2.end_time >= a1.start_time
                    )
                    GROUP BY a1.start_time
                )
            ''', (session_id,))
            
            parallel_result = cursor.fetchone()
            if parallel_result and parallel_result[0]:
                session_parallel_factor.labels(session_id=short_id).set(parallel_result[0])
    
    def _collect_parallel_metrics(self, cursor):
        """Collect parallel execution metrics"""
        # Find currently running agents (started but not ended)
        cursor.execute('''
            SELECT COUNT(*) FROM agent_invocations
            WHERE start_time IS NOT NULL 
            AND end_time IS NULL
            AND agent_name != 'unknown'
        ''')
        
        parallel_count = cursor.fetchone()[0]
        parallel_executions_current.set(parallel_count)
    
    def _collect_success_metrics(self, cursor):
        """Calculate and expose success rates"""
        cursor.execute('''
            SELECT agent_name,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as success,
                   COUNT(*) as total
            FROM agent_invocations
            WHERE agent_name != 'unknown'
            GROUP BY agent_name
        ''')
        
        for agent, success, total in cursor.fetchall():
            if total > 0:
                rate = (success / total) * 100
                agent_success_rate.labels(agent_name=agent).set(rate)
    
    def _collect_database_info(self, cursor):
        """Collect database metadata"""
        # Get database size
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        
        # Get total unique agents
        cursor.execute('''
            SELECT COUNT(DISTINCT agent_name) FROM agent_invocations
            WHERE agent_name != 'unknown'
        ''')
        unique_agents = cursor.fetchone()[0]
        total_agents_gauge.set(unique_agents)
        
        # Get row counts
        cursor.execute('SELECT COUNT(*) FROM agent_invocations')
        total_invocations = cursor.fetchone()[0]
        
        database_info.info({
            'path': str(self.db_path),
            'size_bytes': str(db_size),
            'total_invocations': str(total_invocations),
            'unique_agents': str(unique_agents)
        })
    
    def _collect_tool_usage_metrics(self, cursor):
        """Collect tool usage metrics by agent"""
        # Check if agent_tool_uses table exists
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='agent_tool_uses'
        ''')
        if not cursor.fetchone():
            return  # Table doesn't exist yet
        
        # Get recent tool usage counts by agent and tool (last 7 days)
        cursor.execute('''
            SELECT agent_name, tool_name, 
                   COUNT(*) as usage_count,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as success_count
            FROM agent_tool_uses
            WHERE agent_name != 'unknown' AND agent_name != 'direct'
            AND (timestamp IS NULL OR datetime(timestamp) > datetime('now', '-7 days'))
            GROUP BY agent_name, tool_name
            HAVING COUNT(*) > 0
            ORDER BY usage_count DESC
            LIMIT 1000
        ''')
        
        tool_uses = cursor.fetchall()
        for agent, tool, count, success_count in tool_uses:
            # Set usage counter
            agent_tool_usage_total.labels(
                agent_name=agent,
                tool_name=tool
            ).set(count)
            
            # Calculate success rate
            if count > 0:
                success_rate = (success_count / count) * 100
                agent_tool_success_rate.labels(
                    agent_name=agent,
                    tool_name=tool
                ).set(success_rate)
        
        # Get recent individual duration records for histogram (last 7 days, limited)
        # This approach observes actual duration values instead of approximating
        # by repeating average values, providing accurate histogram data
        cursor.execute('''
            SELECT agent_name, tool_name, duration_seconds
            FROM agent_tool_uses
            WHERE agent_name != 'unknown' AND agent_name != 'direct'
            AND duration_seconds IS NOT NULL AND duration_seconds > 0
            AND (timestamp IS NULL OR datetime(timestamp) > datetime('now', '-7 days'))
            ORDER BY timestamp DESC
            LIMIT 5000
        ''')
        
        duration_records = cursor.fetchall()
        for agent, tool, duration in duration_records:
            # Observe actual duration values in histogram
            agent_tool_duration_seconds.labels(
                agent_name=agent,
                tool_name=tool
            ).observe(duration)
        
        # Calculate tools per agent invocation (recent data only)
        cursor.execute('''
            SELECT agent_name, 
                   AVG(tool_count) as avg_tools
            FROM (
                SELECT agent_name, agent_invocation_id, 
                       COUNT(*) as tool_count
                FROM agent_tool_uses
                WHERE agent_name != 'unknown' AND agent_name != 'direct'
                AND (timestamp IS NULL OR datetime(timestamp) > datetime('now', '-7 days'))
                GROUP BY agent_name, agent_invocation_id
                LIMIT 1000
            )
            GROUP BY agent_name
        ''')
        
        for agent, avg_tools in cursor.fetchall():
            if avg_tools:
                tools_per_agent_invocation.labels(agent_name=agent).set(avg_tools)
        
        # Calculate tool diversity (recent data only)
        cursor.execute('''
            SELECT agent_name,
                   COUNT(DISTINCT tool_name) as unique_tools,
                   COUNT(*) as total_uses
            FROM agent_tool_uses
            WHERE agent_name != 'unknown' AND agent_name != 'direct'
            AND (timestamp IS NULL OR datetime(timestamp) > datetime('now', '-7 days'))
            GROUP BY agent_name
            HAVING COUNT(*) > 0
            ORDER BY total_uses DESC
            LIMIT 100
        ''')
        
        for agent, unique_tools, total_uses in cursor.fetchall():
            if total_uses > 0:
                diversity = unique_tools / total_uses
                agent_tool_diversity.labels(agent_name=agent).set(diversity)
        
        # Find primary tool for each agent (recent data only)
        cursor.execute('''
            SELECT agent_name, tool_name, COUNT(*) as count
            FROM agent_tool_uses
            WHERE agent_name != 'unknown' AND agent_name != 'direct'
            AND (timestamp IS NULL OR datetime(timestamp) > datetime('now', '-7 days'))
            GROUP BY agent_name, tool_name
            HAVING COUNT(*) > 0
            ORDER BY agent_name, count DESC
            LIMIT 500
        ''')
        
        current_agent = None
        for agent, tool, count in cursor.fetchall():
            if agent != current_agent:
                # This is the most used tool for this agent
                agent_primary_tool.info({
                    'agent_name': agent,
                    'primary_tool': tool,
                    'usage_count': str(count)
                })
                current_agent = agent
    
    def run_forever(self, port=9090):
        """Run the metrics collection loop with graceful shutdown support"""
        logger.info(f"Starting Prometheus exporter on port {port}")
        logger.info(f"Metrics available at http://localhost:{port}/metrics")
        logger.info(f"Database: {self.db_path}")
        logger.info("Press Ctrl+C to shutdown gracefully")
        logger.info("-" * 60)
        
        # Start HTTP server
        start_http_server(port, registry=registry)
        
        # Initial collection
        self.collect_metrics()
        logger.info("Initial metrics collected")
        
        # Collection loop with shutdown check
        while not self.shutdown_requested:
            # Use shorter sleep intervals to be more responsive to shutdown
            for _ in range(int(self.update_interval)):
                if self.shutdown_requested:
                    break
                time.sleep(1)
            
            if not self.shutdown_requested:
                self.collect_metrics()
                logger.debug("Metrics updated")
        
        # Graceful shutdown
        logger.info("Performing graceful shutdown...")
        logger.info("Exporter stopped successfully")

def main():
    parser = argparse.ArgumentParser(
        description='Prometheus exporter for agent workflow metrics'
    )
    parser.add_argument(
        '--port', 
        type=int, 
        default=9090,
        help='Port to expose metrics on (default: 9090)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=15,
        help='Update interval in seconds (default: 15)'
    )
    parser.add_argument(
        '--db',
        type=str,
        default=str(DB_PATH),
        help='Path to SQLite database'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    logger.setLevel(getattr(logging, args.log_level))
    
    # Create collector and run
    collector = MetricsCollector(Path(args.db))
    collector.update_interval = args.interval
    
    try:
        collector.run_forever(port=args.port)
    except KeyboardInterrupt:
        # Signal handler will handle this, just exit cleanly
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())