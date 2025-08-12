#!/usr/bin/env python3
"""
Query Tool for Agent Workflow Logs
Provides easy access to logged data with various filters and formats
"""

import sqlite3
import json
from pathlib import Path
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate

# Setup paths
TOOLS_DIR = Path(__file__).parent
PROJECT_DIR = TOOLS_DIR.parent
LOGS_DIR = PROJECT_DIR / "logs"
DB_PATH = LOGS_DIR / "agent_workflow.db"

def list_sessions(limit=10):
    """List recent sessions"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT session_id, start_time, end_time, status
        FROM sessions
        ORDER BY start_time DESC
        LIMIT ?
    ''', (limit,))
    
    sessions = cursor.fetchall()
    conn.close()
    
    if not sessions:
        print("No sessions found")
        return
    
    # Format as table
    headers = ["Session ID", "Start Time", "Duration", "Status"]
    rows = []
    
    for session_id, start, end, status in sessions:
        duration = "ongoing"
        if end:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            duration = str(end_dt - start_dt).split('.')[0]  # Remove microseconds
        
        # Shorten session ID for display
        short_id = session_id[:12] + "..."
        
        rows.append([short_id, start.split('T')[1][:8], duration, status])
    
    print(tabulate(rows, headers=headers, tablefmt="grid"))

def show_session_agents(session_id):
    """Show all agents invoked in a session"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT agent_name, phase, start_time, end_time, status
        FROM agent_invocations
        WHERE session_id = ? AND agent_name != 'unknown'
        ORDER BY timestamp
    ''', (session_id,))
    
    invocations = cursor.fetchall()
    conn.close()
    
    if not invocations:
        print(f"No agents found for session {session_id}")
        return
    
    headers = ["Agent", "Phase", "Start", "Duration", "Status"]
    rows = []
    
    for agent, phase, start, end, status in invocations:
        duration = "N/A"
        if start and end:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            duration = f"{(end_dt - start_dt).total_seconds():.2f}s"
        
        start_time = start.split('T')[1][:8] if start else "N/A"
        
        rows.append([agent, phase, start_time, duration, status])
    
    print(f"\nAgents invoked in session {session_id[:12]}...")
    print(tabulate(rows, headers=headers, tablefmt="grid"))

def find_patterns(min_occurrences=3):
    """Find common agent invocation patterns"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Find sequences of 2 agents
    cursor.execute('''
        WITH agent_sequences AS (
            SELECT 
                session_id,
                agent_name,
                LAG(agent_name) OVER (PARTITION BY session_id ORDER BY timestamp) as prev_agent,
                timestamp
            FROM agent_invocations
            WHERE agent_name != 'unknown'
        )
        SELECT 
            prev_agent || ' → ' || agent_name as pattern,
            COUNT(*) as occurrences
        FROM agent_sequences
        WHERE prev_agent IS NOT NULL
        GROUP BY pattern
        HAVING occurrences >= ?
        ORDER BY occurrences DESC
        LIMIT 20
    ''', (min_occurrences,))
    
    patterns = cursor.fetchall()
    conn.close()
    
    if not patterns:
        print("No patterns found")
        return
    
    print("\n🔄 Common Agent Patterns")
    print("=" * 60)
    
    for pattern, count in patterns:
        bar = "█" * min(count * 2, 40)
        print(f"{pattern:40} [{count:3}] {bar}")

def show_agent_prompts(agent_name, limit=5):
    """Show recent prompts for a specific agent"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT prompt, timestamp, session_id
        FROM agent_invocations
        WHERE agent_name = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (agent_name, limit))
    
    prompts = cursor.fetchall()
    conn.close()
    
    if not prompts:
        print(f"No prompts found for agent '{agent_name}'")
        return
    
    print(f"\n📝 Recent prompts for {agent_name}")
    print("=" * 60)
    
    for i, (prompt, timestamp, session_id) in enumerate(prompts, 1):
        print(f"\n[{i}] {timestamp} (session: {session_id[:8]}...)")
        print("-" * 40)
        # Truncate long prompts
        if len(prompt) > 200:
            print(prompt[:200] + "...")
        else:
            print(prompt)

def export_data(session_id=None, format='json'):
    """Export log data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if session_id:
        cursor.execute('''
            SELECT * FROM agent_invocations
            WHERE session_id = ?
            ORDER BY timestamp
        ''', (session_id,))
        filename = f"export_session_{session_id[:8]}.{format}"
    else:
        cursor.execute('''
            SELECT * FROM agent_invocations
            ORDER BY timestamp DESC
            LIMIT 1000
        ''')
        filename = f"export_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
    
    invocations = cursor.fetchall()
    
    # Get column names
    cursor.execute('PRAGMA table_info(agent_invocations)')
    columns = [col[1] for col in cursor.fetchall()]
    
    conn.close()
    
    if format == 'json':
        data = []
        for row in invocations:
            data.append(dict(zip(columns, row)))
        
        output_file = LOGS_DIR / filename
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"Exported {len(data)} records to {output_file}")
    
    elif format == 'csv':
        import csv
        output_file = LOGS_DIR / filename
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(invocations)
        
        print(f"Exported {len(invocations)} records to {output_file}")

def search_logs(query, field='prompt'):
    """Search logs for specific content"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    valid_fields = ['prompt', 'agent_name', 'error', 'result_summary']
    if field not in valid_fields:
        print(f"Invalid field. Choose from: {', '.join(valid_fields)}")
        return
    
    cursor.execute(f'''
        SELECT session_id, agent_name, timestamp, {field}
        FROM agent_invocations
        WHERE {field} LIKE ?
        ORDER BY timestamp DESC
        LIMIT 20
    ''', (f'%{query}%',))
    
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        print(f"No results found for '{query}' in {field}")
        return
    
    print(f"\n🔍 Search results for '{query}' in {field}")
    print("=" * 60)
    
    for session_id, agent, timestamp, content in results:
        print(f"\n{timestamp} | {agent} | {session_id[:8]}...")
        print("-" * 40)
        # Highlight search term
        highlighted = content.replace(query, f"**{query}**")
        if len(highlighted) > 200:
            print(highlighted[:200] + "...")
        else:
            print(highlighted)

def main():
    parser = argparse.ArgumentParser(description='Query agent workflow logs')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List sessions
    list_parser = subparsers.add_parser('sessions', help='List recent sessions')
    list_parser.add_argument('--limit', type=int, default=10, help='Number of sessions to show')
    
    # Show session details
    show_parser = subparsers.add_parser('show', help='Show session details')
    show_parser.add_argument('session_id', help='Session ID to show')
    
    # Find patterns
    patterns_parser = subparsers.add_parser('patterns', help='Find common patterns')
    patterns_parser.add_argument('--min', type=int, default=3, help='Minimum occurrences')
    
    # Show agent prompts
    prompts_parser = subparsers.add_parser('prompts', help='Show agent prompts')
    prompts_parser.add_argument('agent', help='Agent name')
    prompts_parser.add_argument('--limit', type=int, default=5, help='Number of prompts')
    
    # Export data
    export_parser = subparsers.add_parser('export', help='Export log data')
    export_parser.add_argument('--session', help='Session ID to export')
    export_parser.add_argument('--format', choices=['json', 'csv'], default='json')
    
    # Search logs
    search_parser = subparsers.add_parser('search', help='Search logs')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--field', default='prompt', help='Field to search')
    
    args = parser.parse_args()
    
    if not DB_PATH.exists():
        print("No logs found. Run some agent workflows first!")
        return
    
    if args.command == 'sessions':
        list_sessions(args.limit)
    elif args.command == 'show':
        show_session_agents(args.session_id)
    elif args.command == 'patterns':
        find_patterns(args.min)
    elif args.command == 'prompts':
        show_agent_prompts(args.agent, args.limit)
    elif args.command == 'export':
        export_data(args.session, args.format)
    elif args.command == 'search':
        search_logs(args.query, args.field)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()