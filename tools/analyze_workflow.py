#!/usr/bin/env python3
"""
Workflow Analyzer for Agent Invocations
Generates statistics and insights from logged agent invocations
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
import argparse
from collections import defaultdict, Counter

# Setup paths
TOOLS_DIR = Path(__file__).parent
PROJECT_DIR = TOOLS_DIR.parent
LOGS_DIR = PROJECT_DIR / "logs"
DB_PATH = LOGS_DIR / "agent_workflow.db"

def get_session_stats(session_id=None):
    """Get statistics for sessions"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if session_id:
        cursor.execute('''
            SELECT * FROM sessions WHERE session_id = ?
        ''', (session_id,))
    else:
        cursor.execute('SELECT * FROM sessions ORDER BY start_time DESC')
    
    sessions = cursor.fetchall()
    conn.close()
    
    return sessions

def get_agent_stats():
    """Get agent usage statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Agent frequency
    cursor.execute('''
        SELECT agent_name, COUNT(*) as count
        FROM agent_invocations
        WHERE agent_name != 'unknown'
        GROUP BY agent_name
        ORDER BY count DESC
    ''')
    agent_frequency = cursor.fetchall()
    
    # Average execution time per agent
    cursor.execute('''
        SELECT agent_name, 
               AVG(CAST((julianday(end_time) - julianday(start_time)) * 86400 AS REAL)) as avg_duration
        FROM agent_invocations
        WHERE end_time IS NOT NULL AND agent_name != 'unknown'
        GROUP BY agent_name
        ORDER BY avg_duration DESC
    ''')
    agent_durations = cursor.fetchall()
    
    # Success/failure rates
    cursor.execute('''
        SELECT agent_name, status, COUNT(*) as count
        FROM agent_invocations
        WHERE agent_name != 'unknown'
        GROUP BY agent_name, status
    ''')
    agent_status = cursor.fetchall()
    
    # Phase distribution
    cursor.execute('''
        SELECT phase, COUNT(*) as count
        FROM agent_invocations
        WHERE phase != 'unknown'
        GROUP BY phase
        ORDER BY count DESC
    ''')
    phase_distribution = cursor.fetchall()
    
    conn.close()
    
    return {
        'frequency': agent_frequency,
        'durations': agent_durations,
        'status': agent_status,
        'phases': phase_distribution
    }

def find_agent_sequences(min_length=2):
    """Find common sequences of agent invocations"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all agent invocations grouped by session
    cursor.execute('''
        SELECT session_id, agent_name, timestamp
        FROM agent_invocations
        WHERE agent_name != 'unknown'
        ORDER BY session_id, timestamp
    ''')
    
    invocations = cursor.fetchall()
    conn.close()
    
    # Group by session
    sessions = defaultdict(list)
    for session_id, agent_name, timestamp in invocations:
        sessions[session_id].append(agent_name)
    
    # Find sequences
    sequences = []
    for session_id, agents in sessions.items():
        for i in range(len(agents) - min_length + 1):
            sequence = tuple(agents[i:i + min_length])
            sequences.append(sequence)
    
    # Count sequences
    sequence_counts = Counter(sequences)
    
    return sequence_counts.most_common(10)

def analyze_parallel_execution():
    """Analyze parallel agent execution patterns"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Find overlapping agent executions
    cursor.execute('''
        SELECT a1.agent_name, a2.agent_name, COUNT(*) as overlap_count
        FROM agent_invocations a1
        JOIN agent_invocations a2 ON a1.session_id = a2.session_id
        WHERE a1.agent_name != a2.agent_name
          AND a1.start_time <= a2.end_time
          AND a1.end_time >= a2.start_time
          AND a1.agent_name != 'unknown'
          AND a2.agent_name != 'unknown'
        GROUP BY a1.agent_name, a2.agent_name
        ORDER BY overlap_count DESC
        LIMIT 10
    ''')
    
    parallel_patterns = cursor.fetchall()
    conn.close()
    
    return parallel_patterns

def identify_bottlenecks():
    """Identify potential bottlenecks in the workflow"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Find slowest agents
    cursor.execute('''
        SELECT agent_name, 
               MAX(CAST((julianday(end_time) - julianday(start_time)) * 86400 AS REAL)) as max_duration,
               AVG(CAST((julianday(end_time) - julianday(start_time)) * 86400 AS REAL)) as avg_duration,
               COUNT(*) as invocation_count
        FROM agent_invocations
        WHERE end_time IS NOT NULL AND agent_name != 'unknown'
        GROUP BY agent_name
        HAVING avg_duration > 10  -- More than 10 seconds average
        ORDER BY avg_duration DESC
    ''')
    
    bottlenecks = cursor.fetchall()
    conn.close()
    
    return bottlenecks

def print_report(session_id=None):
    """Print comprehensive analysis report"""
    print("=" * 60)
    print("AGENT WORKFLOW ANALYSIS REPORT")
    print("=" * 60)
    
    # Session stats
    sessions = get_session_stats(session_id)
    if sessions:
        print("\n📊 SESSION SUMMARY")
        print("-" * 40)
        for session in sessions[:5]:  # Show last 5 sessions
            session_id, start, end, status, *_ = session
            duration = "ongoing"
            if end:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
                duration = str(end_dt - start_dt)
            print(f"  {session_id[:8]}... | {status:10} | Duration: {duration}")
    
    # Agent statistics
    stats = get_agent_stats()
    
    print("\n🤖 AGENT USAGE FREQUENCY")
    print("-" * 40)
    for agent, count in stats['frequency'][:10]:
        bar = "█" * min(count, 20)
        print(f"  {agent:25} {count:3} {bar}")
    
    print("\n⏱️  AVERAGE EXECUTION TIME (seconds)")
    print("-" * 40)
    for agent, duration in stats['durations'][:10]:
        if duration:
            print(f"  {agent:25} {duration:6.2f}s")
    
    print("\n📈 PHASE DISTRIBUTION")
    print("-" * 40)
    for phase, count in stats['phases']:
        bar = "█" * min(count, 20)
        print(f"  {phase:15} {count:3} {bar}")
    
    # Common sequences
    sequences = find_agent_sequences(3)
    if sequences:
        print("\n🔄 COMMON AGENT SEQUENCES (3-agent chains)")
        print("-" * 40)
        for sequence, count in sequences[:5]:
            sequence_str = " → ".join(sequence)
            print(f"  [{count:2}x] {sequence_str}")
    
    # Parallel patterns
    parallel = analyze_parallel_execution()
    if parallel:
        print("\n⚡ PARALLEL EXECUTION PATTERNS")
        print("-" * 40)
        for agent1, agent2, count in parallel[:5]:
            print(f"  {agent1} || {agent2} ({count} times)")
    
    # Bottlenecks
    bottlenecks = identify_bottlenecks()
    if bottlenecks:
        print("\n🚨 POTENTIAL BOTTLENECKS")
        print("-" * 40)
        for agent, max_dur, avg_dur, count in bottlenecks:
            print(f"  {agent:25} Avg: {avg_dur:6.2f}s, Max: {max_dur:6.2f}s ({count} runs)")
    
    print("\n" + "=" * 60)

def export_session_data(session_id, format='json'):
    """Export session data for external analysis"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM agent_invocations
        WHERE session_id = ?
        ORDER BY timestamp
    ''', (session_id,))
    
    invocations = cursor.fetchall()
    conn.close()
    
    if format == 'json':
        # Convert to JSON format
        data = []
        columns = ['id', 'timestamp', 'session_id', 'event_type', 'phase', 
                  'agent_name', 'agent_type', 'model', 'prompt', 'parent_agent',
                  'ticket_id', 'start_time', 'end_time', 'duration_seconds',
                  'status', 'error', 'result_summary', 'raw_input', 'raw_output']
        
        for row in invocations:
            data.append(dict(zip(columns, row)))
        
        output_file = LOGS_DIR / f"export_{session_id}.json"
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Exported to {output_file}")
    
    return invocations

def main():
    parser = argparse.ArgumentParser(description='Analyze agent workflow logs')
    parser.add_argument('--session', help='Analyze specific session')
    parser.add_argument('--export', help='Export session data', metavar='SESSION_ID')
    parser.add_argument('--format', default='json', help='Export format (json)')
    parser.add_argument('--sequences', type=int, default=3, help='Sequence length to analyze')
    args = parser.parse_args()
    
    if not DB_PATH.exists():
        print("No logs found. Run some agent workflows first!")
        return
    
    if args.export:
        export_session_data(args.export, args.format)
    else:
        print_report(args.session)

if __name__ == "__main__":
    main()