#!/usr/bin/env python3
"""
Hook Data Verification Tool
Compares hook captured data with Claude transcript files to identify missing fields
"""

import json
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
import argparse
from typing import Dict, Set, List, Any

# Setup paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
LOGS_DIR = PROJECT_DIR / "logs"
DB_PATH = LOGS_DIR / "agent_workflow.db"
SESSIONS_DIR = LOGS_DIR / "sessions"
CLAUDE_DIR = Path.home() / ".claude" / "projects"

def find_transcript_file(session_id: str) -> Path:
    """Find the transcript file for a given session ID"""
    # First check if we have it in the database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT json_extract(metadata, '$.transcript_path') 
        FROM sessions 
        WHERE session_id = ?
    """, (session_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        transcript_path = Path(result[0])
        if transcript_path.exists():
            return transcript_path
    
    # Otherwise search in Claude directory
    for project_dir in CLAUDE_DIR.glob("*"):
        transcript = project_dir / f"{session_id}.jsonl"
        if transcript.exists():
            return transcript
    
    return None

def parse_transcript(transcript_path: Path) -> List[Dict]:
    """Parse a JSONL transcript file"""
    events = []
    with open(transcript_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Error parsing line: {e}", file=sys.stderr)
    return events

def extract_hook_events(transcript_events: List[Dict]) -> Dict[str, List[Dict]]:
    """Extract hook-related events from transcript"""
    hook_events = {
        'SessionStart': [],
        'PreToolUse': [],
        'PostToolUse': [],
        'Stop': [],
        'SubagentStop': [],
        'Notification': []
    }
    
    for event in transcript_events:
        # Look for hook executions in system messages
        if event.get('type') == 'system':
            content = event.get('content', '')
            if 'SessionStart:' in content:
                hook_events['SessionStart'].append(event)
            elif '[HOOK]' in content:
                # Parse hook output messages
                if 'Agent invoked:' in content:
                    hook_events['PreToolUse'].append(event)
                elif 'Agent completed:' in content:
                    hook_events['PostToolUse'].append(event)
        
        # Look for tool uses
        if event.get('type') == 'assistant':
            message = event.get('message', {})
            if message.get('content'):
                for content_item in message['content']:
                    if content_item.get('type') == 'tool_use':
                        hook_events['PreToolUse'].append(event)
    
    return hook_events

def get_database_records(session_id: str) -> Dict[str, Any]:
    """Get all database records for a session"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get session record
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    session = cursor.fetchone()
    
    # Get agent invocations
    cursor.execute("SELECT * FROM agent_invocations WHERE session_id = ?", (session_id,))
    invocations = cursor.fetchall()
    
    # Get tool uses
    cursor.execute("SELECT * FROM agent_tool_uses WHERE session_id = ?", (session_id,))
    tool_uses = cursor.fetchall()
    
    conn.close()
    
    return {
        'session': session,
        'invocations': invocations,
        'tool_uses': tool_uses
    }

def extract_available_fields(transcript_events: List[Dict]) -> Set[str]:
    """Extract all unique fields from transcript events"""
    fields = set()
    
    def extract_fields_recursive(obj, prefix=''):
        if isinstance(obj, dict):
            for key, value in obj.items():
                field_name = f"{prefix}.{key}" if prefix else key
                fields.add(field_name)
                if isinstance(value, (dict, list)):
                    extract_fields_recursive(value, field_name)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    extract_fields_recursive(item, prefix)
    
    for event in transcript_events:
        extract_fields_recursive(event)
    
    return fields

def compare_fields(transcript_fields: Set[str], captured_fields: Set[str]) -> Dict[str, Set[str]]:
    """Compare fields available in transcript vs captured in database"""
    return {
        'captured': captured_fields,
        'available': transcript_fields,
        'missing': transcript_fields - captured_fields,
        'extra': captured_fields - transcript_fields
    }

def generate_report(session_id: str, comparison: Dict, stats: Dict) -> str:
    """Generate a verification report"""
    report = f"""
# Hook Data Verification Report
Session: {session_id}
Generated: {datetime.now().isoformat()}

## Summary Statistics
- Transcript Events: {stats['transcript_events']}
- Database Records: {stats['db_records']}
- Agent Invocations: {stats['agent_invocations']}
- Tool Uses: {stats['tool_uses']}

## Field Coverage Analysis
- Total Fields Available: {len(comparison['available'])}
- Fields Captured: {len(comparison['captured'])}
- Missing Fields: {len(comparison['missing'])}

## Critical Missing Fields
"""
    
    # Categorize missing fields
    critical_missing = {
        'Performance': [],
        'Relationships': [],
        'Context': [],
        'Metadata': []
    }
    
    for field in comparison['missing']:
        if 'usage' in field or 'token' in field or 'duration' in field:
            critical_missing['Performance'].append(field)
        elif 'uuid' in field.lower() or 'parent' in field:
            critical_missing['Relationships'].append(field)
        elif 'git' in field or 'version' in field or 'cwd' in field:
            critical_missing['Context'].append(field)
        else:
            critical_missing['Metadata'].append(field)
    
    for category, fields in critical_missing.items():
        if fields:
            report += f"\n### {category}\n"
            for field in sorted(fields)[:10]:  # Limit to top 10
                report += f"- `{field}`\n"
    
    report += """
## Recommendations

1. **High Priority Updates**:
   - Add transcript_path to all hook events
   - Capture token usage statistics
   - Store parent/child relationships

2. **Data Enhancement**:
   - Parse thinking content for insights
   - Extract git branch and version
   - Track tool use IDs for correlation

3. **Quality Improvements**:
   - Fix duration calculation
   - Populate model field
   - Add error categorization
"""
    
    return report

def main():
    parser = argparse.ArgumentParser(description='Verify hook data completeness')
    parser.add_argument('--session', help='Session ID to verify')
    parser.add_argument('--latest', action='store_true', help='Verify latest session')
    parser.add_argument('--all', action='store_true', help='Verify all sessions')
    parser.add_argument('--output', help='Output file for report')
    args = parser.parse_args()
    
    # Determine which sessions to verify
    sessions_to_verify = []
    
    if args.session:
        sessions_to_verify = [args.session]
    elif args.latest or (not args.all and not args.session):
        # Get latest session
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id FROM sessions 
            ORDER BY start_time DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        conn.close()
        if result:
            sessions_to_verify = [result[0]]
    elif args.all:
        # Get all sessions
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT session_id FROM sessions")
        sessions_to_verify = [row[0] for row in cursor.fetchall()]
        conn.close()
    
    if not sessions_to_verify:
        print("No sessions found to verify", file=sys.stderr)
        sys.exit(1)
    
    # Verify each session
    all_reports = []
    for session_id in sessions_to_verify:
        print(f"Verifying session: {session_id}", file=sys.stderr)
        
        # Find transcript file
        transcript_path = find_transcript_file(session_id)
        if not transcript_path:
            print(f"  ⚠️  No transcript found for session {session_id}", file=sys.stderr)
            continue
        
        print(f"  Found transcript: {transcript_path}", file=sys.stderr)
        
        # Parse transcript
        transcript_events = parse_transcript(transcript_path)
        
        # Get database records
        db_records = get_database_records(session_id)
        
        # Extract fields
        transcript_fields = extract_available_fields(transcript_events)
        
        # Define captured fields (from our database schema)
        captured_fields = {
            'session_id', 'start_time', 'end_time', 'status', 'cwd',
            'timestamp', 'event_type', 'phase', 'agent_name', 'agent_type',
            'model', 'prompt', 'parent_agent', 'ticket_id', 'duration_seconds',
            'error', 'result_summary', 'raw_input', 'raw_output',
            'tool_name', 'tool_input', 'tool_output', 'sequence_number'
        }
        
        # Compare fields
        comparison = compare_fields(transcript_fields, captured_fields)
        
        # Generate statistics
        stats = {
            'transcript_events': len(transcript_events),
            'db_records': 1 if db_records['session'] else 0,
            'agent_invocations': len(db_records['invocations']),
            'tool_uses': len(db_records['tool_uses'])
        }
        
        # Generate report
        report = generate_report(session_id, comparison, stats)
        all_reports.append(report)
        
        # Print summary
        print(f"  ✅ Verified: {len(comparison['captured'])} fields captured", file=sys.stderr)
        print(f"  ⚠️  Missing: {len(comparison['missing'])} fields available but not captured", file=sys.stderr)
    
    # Output results
    final_report = "\n\n---\n\n".join(all_reports)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(final_report)
        print(f"Report saved to: {args.output}", file=sys.stderr)
    else:
        print(final_report)

if __name__ == "__main__":
    main()