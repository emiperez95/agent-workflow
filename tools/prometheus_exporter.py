#!/usr/bin/env python3
"""
Prometheus Exporter for Agent Workflow Metrics
Exposes SQLite database metrics in Prometheus format for Grafana visualization
"""

import sqlite3
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from prometheus_client import start_http_server, Counter, Histogram, Gauge, Info
from prometheus_client.core import CollectorRegistry
from collections import defaultdict

# Setup paths
TOOLS_DIR = Path(__file__).parent
PROJECT_DIR = TOOLS_DIR.parent
LOGS_DIR = PROJECT_DIR / "logs"
DB_PATH = LOGS_DIR / "agent_workflow.db"

# Create a custom registry to avoid conflicts
registry = CollectorRegistry()

# Define Prometheus metrics

# Agent-specific metrics
agent_invocation_total = Counter(
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

phase_distribution_total = Counter(
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
agent_tool_usage_total = Counter(
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

class MetricsCollector:
    """Collects and exposes metrics from SQLite database"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.last_update = None
        self.update_interval = 15  # seconds
        
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def collect_metrics(self):
        """Collect all metrics from database"""
        if not self.db_path.exists():
            print(f"Database not found at {self.db_path}")
            return
        
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
            
        except Exception as e:
            print(f"Error collecting metrics: {e}")
    
    def _collect_invocation_metrics(self, cursor):
        """Collect agent invocation metrics"""
        # Get all invocations with timing
        cursor.execute('''
            SELECT agent_name, phase, status, model,
                   start_time, end_time,
                   (julianday(end_time) - julianday(start_time)) * 86400 as duration
            FROM agent_invocations
            WHERE agent_name != 'unknown'
        ''')
        
        invocations = cursor.fetchall()
        
        # Reset counters (they accumulate)
        phase_counts = defaultdict(int)
        
        for agent, phase, status, model, start, end, duration in invocations:
            # Default values for None
            phase = phase or 'unknown'
            status = status or 'unknown'
            model = model or 'unknown'
            
            # Count invocations
            agent_invocation_total.labels(
                agent_name=agent,
                phase=phase,
                status=status,
                model=model
            )._value._value = 0  # Reset before incrementing
            
            agent_invocation_total.labels(
                agent_name=agent,
                phase=phase,
                status=status,
                model=model
            ).inc()
            
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
                except:
                    pass
            
            # Track errors
            if status in ['failed', 'error']:
                agent_error_total.labels(agent_name=agent, phase=phase).inc()
        
        # Update phase distribution
        for phase, count in phase_counts.items():
            phase_distribution_total.labels(phase=phase)._value._value = count
    
    def _collect_session_metrics(self, cursor):
        """Collect session-related metrics"""
        # Get session durations
        cursor.execute('''
            SELECT session_id, start_time, end_time,
                   (julianday(end_time) - julianday(start_time)) * 86400 as duration
            FROM sessions
            WHERE end_time IS NOT NULL
        ''')
        
        sessions = cursor.fetchall()
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
                except:
                    pass
            
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
                        except:
                            pass
                    
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
                except:
                    pass
            
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
        
        # Get tool usage counts by agent and tool
        cursor.execute('''
            SELECT agent_name, tool_name, 
                   COUNT(*) as usage_count,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as success_count,
                   AVG(duration_seconds) as avg_duration
            FROM agent_tool_uses
            WHERE agent_name != 'unknown' AND agent_name != 'direct'
            GROUP BY agent_name, tool_name
        ''')
        
        tool_uses = cursor.fetchall()
        for agent, tool, count, success_count, avg_duration in tool_uses:
            # Set usage counter
            agent_tool_usage_total.labels(
                agent_name=agent,
                tool_name=tool
            )._value._value = count
            
            # Set duration histogram
            if avg_duration:
                for _ in range(int(count)):  # Approximate histogram
                    agent_tool_duration_seconds.labels(
                        agent_name=agent,
                        tool_name=tool
                    ).observe(avg_duration)
            
            # Calculate success rate
            if count > 0:
                success_rate = (success_count / count) * 100
                agent_tool_success_rate.labels(
                    agent_name=agent,
                    tool_name=tool
                ).set(success_rate)
        
        # Calculate tools per agent invocation
        cursor.execute('''
            SELECT agent_name, 
                   AVG(tool_count) as avg_tools
            FROM (
                SELECT agent_name, agent_invocation_id, 
                       COUNT(*) as tool_count
                FROM agent_tool_uses
                WHERE agent_name != 'unknown' AND agent_name != 'direct'
                GROUP BY agent_name, agent_invocation_id
            )
            GROUP BY agent_name
        ''')
        
        for agent, avg_tools in cursor.fetchall():
            if avg_tools:
                tools_per_agent_invocation.labels(agent_name=agent).set(avg_tools)
        
        # Calculate tool diversity
        cursor.execute('''
            SELECT agent_name,
                   COUNT(DISTINCT tool_name) as unique_tools,
                   COUNT(*) as total_uses
            FROM agent_tool_uses
            WHERE agent_name != 'unknown' AND agent_name != 'direct'
            GROUP BY agent_name
        ''')
        
        for agent, unique_tools, total_uses in cursor.fetchall():
            if total_uses > 0:
                diversity = unique_tools / total_uses
                agent_tool_diversity.labels(agent_name=agent).set(diversity)
        
        # Find primary tool for each agent
        cursor.execute('''
            SELECT agent_name, tool_name, COUNT(*) as count
            FROM agent_tool_uses
            WHERE agent_name != 'unknown' AND agent_name != 'direct'
            GROUP BY agent_name, tool_name
            ORDER BY agent_name, count DESC
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
        """Run the metrics collection loop"""
        print(f"Starting Prometheus exporter on port {port}")
        print(f"Metrics available at http://localhost:{port}/metrics")
        print(f"Database: {self.db_path}")
        print("-" * 60)
        
        # Start HTTP server
        start_http_server(port, registry=registry)
        
        # Initial collection
        self.collect_metrics()
        print(f"[{datetime.now().isoformat()}] Initial metrics collected")
        
        # Collection loop
        while True:
            time.sleep(self.update_interval)
            self.collect_metrics()
            print(f"[{datetime.now().isoformat()}] Metrics updated")

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
    
    args = parser.parse_args()
    
    # Create collector and run
    collector = MetricsCollector(Path(args.db))
    collector.update_interval = args.interval
    
    try:
        collector.run_forever(port=args.port)
    except KeyboardInterrupt:
        print("\nShutting down exporter...")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())