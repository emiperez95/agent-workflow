#!/usr/bin/env python3
"""
Transcript Parser for Claude Code
Extracts rich data from Claude transcript JSONL files to supplement hook data
"""

import json
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
import argparse
from typing import Dict, List, Any, Optional

# Setup paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
LOGS_DIR = PROJECT_DIR / "logs"
DB_PATH = LOGS_DIR / "agent_workflow.db"
CLAUDE_DIR = Path.home() / ".claude" / "projects"

def init_enhanced_database():
    """Create enhanced tables for transcript data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create transcript_events table for rich data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transcript_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            uuid TEXT UNIQUE,
            parent_uuid TEXT,
            timestamp TIMESTAMP,
            event_type TEXT,
            tool_use_id TEXT,
            git_branch TEXT,
            claude_version TEXT,
            user_type TEXT,
            is_meta BOOLEAN,
            is_sidechain BOOLEAN,
            content TEXT,
            message JSON,
            usage JSON,
            thinking TEXT,
            duration_ms REAL,
            tokens_total INTEGER,
            tokens_input INTEGER,
            tokens_output INTEGER,
            tokens_cache_read INTEGER,
            tokens_cache_create INTEGER,
            service_tier TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    ''')
    
    # Create thinking_logs table for Claude's reasoning
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS thinking_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            event_uuid TEXT,
            timestamp TIMESTAMP,
            thinking_content TEXT,
            signature TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id),
            FOREIGN KEY (event_uuid) REFERENCES transcript_events(uuid)
        )
    ''')
    
    # Create tool_relationships table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tool_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            parent_uuid TEXT,
            child_uuid TEXT,
            relationship_type TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    ''')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transcript_session ON transcript_events(session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transcript_uuid ON transcript_events(uuid)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transcript_parent ON transcript_events(parent_uuid)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_parent ON tool_relationships(parent_uuid)')
    
    conn.commit()
    conn.close()

def find_transcript_files(session_id: Optional[str] = None) -> List[Path]:
    """Find transcript files for sessions"""
    transcript_files = []
    
    if session_id:
        # Find specific session transcript
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
                transcript_files.append(transcript_path)
    else:
        # Find all transcript files
        for project_dir in CLAUDE_DIR.glob("*"):
            for transcript in project_dir.glob("*.jsonl"):
                transcript_files.append(transcript)
    
    return transcript_files

def parse_transcript_event(event: Dict) -> Dict[str, Any]:
    """Parse a single transcript event into structured data"""
    parsed = {
        'uuid': event.get('uuid'),
        'parent_uuid': event.get('parentUuid'),
        'timestamp': event.get('timestamp'),
        'event_type': event.get('type'),
        'tool_use_id': event.get('toolUseID'),
        'git_branch': event.get('gitBranch'),
        'claude_version': event.get('version'),
        'user_type': event.get('userType'),
        'is_meta': event.get('isMeta', False),
        'is_sidechain': event.get('isSidechain', False),
        'session_id': event.get('sessionId'),
        'content': None,
        'thinking': None,
        'usage': {},
        'duration_ms': None
    }
    
    # Extract content based on event type
    if event.get('content'):
        parsed['content'] = event['content']
    elif event.get('message'):
        message = event['message']
        parsed['message'] = json.dumps(message)
        
        # Extract usage statistics
        if message.get('usage'):
            usage = message['usage']
            parsed['usage'] = json.dumps(usage)
            parsed['tokens_input'] = usage.get('input_tokens', 0)
            parsed['tokens_output'] = usage.get('output_tokens', 0)
            parsed['tokens_cache_read'] = usage.get('cache_read_input_tokens', 0)
            parsed['tokens_cache_create'] = usage.get('cache_creation_input_tokens', 0)
            parsed['service_tier'] = usage.get('service_tier', '')
            parsed['tokens_total'] = (parsed['tokens_input'] + parsed['tokens_output'] + 
                                     parsed['tokens_cache_read'] + parsed['tokens_cache_create'])
        
        # Extract thinking content
        if message.get('content'):
            content = message['content']
            if isinstance(content, list):
                for content_item in content:
                    if isinstance(content_item, dict) and content_item.get('type') == 'thinking':
                        parsed['thinking'] = content_item.get('thinking', '')
                        break
    
    # Extract duration from tool results
    if event.get('toolUseResult'):
        result = event['toolUseResult']
        if isinstance(result, dict) and result.get('durationMs'):
            parsed['duration_ms'] = result['durationMs']
    
    return parsed

def store_transcript_data(parsed_events: List[Dict], session_id: str):
    """Store parsed transcript data in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for event in parsed_events:
        # Skip if already exists
        cursor.execute('SELECT id FROM transcript_events WHERE uuid = ?', (event['uuid'],))
        if cursor.fetchone():
            continue
        
        # Insert main event
        cursor.execute('''
            INSERT INTO transcript_events (
                session_id, uuid, parent_uuid, timestamp, event_type,
                tool_use_id, git_branch, claude_version, user_type,
                is_meta, is_sidechain, content, message, usage,
                thinking, duration_ms, tokens_total, tokens_input,
                tokens_output, tokens_cache_read, tokens_cache_create,
                service_tier
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id, event.get('uuid'), event.get('parent_uuid'),
            event.get('timestamp'), event.get('event_type'),
            event.get('tool_use_id'), event.get('git_branch'),
            event.get('claude_version'), event.get('user_type'),
            event.get('is_meta'), event.get('is_sidechain'),
            event.get('content'), event.get('message'),
            json.dumps(event.get('usage', {})) if event.get('usage') else None,
            event.get('thinking'), event.get('duration_ms'),
            event.get('tokens_total'), event.get('tokens_input'),
            event.get('tokens_output'), event.get('tokens_cache_read'),
            event.get('tokens_cache_create'), event.get('service_tier')
        ))
        
        # Store thinking separately if present
        if event.get('thinking'):
            cursor.execute('''
                INSERT INTO thinking_logs (
                    session_id, event_uuid, timestamp, thinking_content
                ) VALUES (?, ?, ?, ?)
            ''', (session_id, event['uuid'], event['timestamp'], event['thinking']))
        
        # Store relationships
        if event.get('parent_uuid'):
            cursor.execute('''
                INSERT INTO tool_relationships (
                    session_id, parent_uuid, child_uuid, 
                    relationship_type, created_at
                ) VALUES (?, ?, ?, ?, ?)
            ''', (session_id, event['parent_uuid'], event['uuid'], 
                  'parent-child', datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def analyze_transcript_data(session_id: str) -> Dict[str, Any]:
    """Analyze parsed transcript data for insights"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get token usage summary
    cursor.execute('''
        SELECT 
            SUM(tokens_total) as total_tokens,
            SUM(tokens_input) as input_tokens,
            SUM(tokens_output) as output_tokens,
            SUM(tokens_cache_read) as cache_read,
            SUM(tokens_cache_create) as cache_create,
            COUNT(DISTINCT uuid) as event_count,
            COUNT(DISTINCT tool_use_id) as tool_use_count
        FROM transcript_events
        WHERE session_id = ?
    ''', (session_id,))
    
    usage_stats = cursor.fetchone()
    
    # Get thinking logs count
    cursor.execute('''
        SELECT COUNT(*) FROM thinking_logs WHERE session_id = ?
    ''', (session_id,))
    thinking_count = cursor.fetchone()[0]
    
    # Get relationship stats
    cursor.execute('''
        SELECT COUNT(*) FROM tool_relationships WHERE session_id = ?
    ''', (session_id,))
    relationship_count = cursor.fetchone()[0]
    
    # Get git branches used
    cursor.execute('''
        SELECT DISTINCT git_branch FROM transcript_events 
        WHERE session_id = ? AND git_branch IS NOT NULL
    ''', (session_id,))
    branches = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        'total_tokens': usage_stats[0] or 0,
        'input_tokens': usage_stats[1] or 0,
        'output_tokens': usage_stats[2] or 0,
        'cache_read_tokens': usage_stats[3] or 0,
        'cache_create_tokens': usage_stats[4] or 0,
        'event_count': usage_stats[5] or 0,
        'tool_use_count': usage_stats[6] or 0,
        'thinking_logs': thinking_count,
        'relationships': relationship_count,
        'git_branches': branches
    }

def main():
    parser = argparse.ArgumentParser(description='Parse Claude transcript files')
    parser.add_argument('--session', help='Session ID to parse')
    parser.add_argument('--all', action='store_true', help='Parse all transcript files')
    parser.add_argument('--analyze', action='store_true', help='Analyze parsed data')
    parser.add_argument('--init', action='store_true', help='Initialize enhanced database')
    args = parser.parse_args()
    
    # Initialize database if requested
    if args.init:
        print("Initializing enhanced database...", file=sys.stderr)
        init_enhanced_database()
        print("✅ Database initialized", file=sys.stderr)
        return
    
    # Find transcript files
    if args.session:
        transcript_files = find_transcript_files(args.session)
        sessions = [args.session]
    elif args.all:
        transcript_files = find_transcript_files()
        sessions = []
        for f in transcript_files:
            # Extract session ID from filename
            session_id = f.stem
            sessions.append(session_id)
    else:
        print("Please specify --session or --all", file=sys.stderr)
        sys.exit(1)
    
    # Initialize database
    init_enhanced_database()
    
    # Parse each transcript
    for transcript_file, session_id in zip(transcript_files, sessions):
        print(f"Parsing transcript for session {session_id}...", file=sys.stderr)
        
        # Parse events
        events = []
        with open(transcript_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        event = json.loads(line)
                        parsed = parse_transcript_event(event)
                        events.append(parsed)
                    except json.JSONDecodeError as e:
                        print(f"  Error parsing line: {e}", file=sys.stderr)
        
        # Store in database
        store_transcript_data(events, session_id)
        print(f"  ✅ Stored {len(events)} events", file=sys.stderr)
        
        # Analyze if requested
        if args.analyze:
            analysis = analyze_transcript_data(session_id)
            print(f"\n📊 Analysis for session {session_id}:")
            print(f"  Total Tokens: {analysis['total_tokens']:,}")
            print(f"  Input Tokens: {analysis['input_tokens']:,}")
            print(f"  Output Tokens: {analysis['output_tokens']:,}")
            print(f"  Cache Read: {analysis['cache_read_tokens']:,}")
            print(f"  Cache Create: {analysis['cache_create_tokens']:,}")
            print(f"  Events: {analysis['event_count']}")
            print(f"  Tool Uses: {analysis['tool_use_count']}")
            print(f"  Thinking Logs: {analysis['thinking_logs']}")
            print(f"  Relationships: {analysis['relationships']}")
            print(f"  Git Branches: {', '.join(analysis['git_branches'])}")

if __name__ == "__main__":
    main()