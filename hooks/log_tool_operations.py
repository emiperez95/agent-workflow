#!/usr/bin/env python3
"""
Tool Operations Logger for Claude Code
Tracks all tool uses within agent context to understand agent behavior patterns
"""

import json
import sys
import os
import sqlite3
from datetime import datetime
from pathlib import Path
import argparse

# Setup paths
HOOKS_DIR = Path(__file__).parent
PROJECT_DIR = HOOKS_DIR.parent
LOGS_DIR = PROJECT_DIR / "logs"
DB_PATH = LOGS_DIR / "agent_workflow.db"
CONTEXT_FILE = LOGS_DIR / "current_agent_context.json"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)

def init_database():
    """Initialize SQLite database with agent_tool_uses table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create agent_tool_uses table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_tool_uses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP,
            session_id TEXT,
            agent_name TEXT,
            agent_invocation_id INTEGER,
            tool_name TEXT,
            tool_input JSON,
            tool_output JSON,
            duration_seconds REAL,
            status TEXT,
            error TEXT,
            sequence_number INTEGER,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    ''')
    
    # Create index for performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_agent_tool_uses_agent 
        ON agent_tool_uses(agent_name, tool_name)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_agent_tool_uses_session 
        ON agent_tool_uses(session_id)
    ''')
    
    conn.commit()
    conn.close()

def get_current_agent_context():
    """Get the currently active agent from context file"""
    if not CONTEXT_FILE.exists():
        return None, None, 0
    
    try:
        with open(CONTEXT_FILE, 'r') as f:
            context = json.load(f)
            return (
                context.get('agent_name', 'unknown'),
                context.get('agent_invocation_id'),
                context.get('tool_sequence_number', 0)
            )
    except:
        return None, None, 0

def update_agent_context(agent_name=None, invocation_id=None, increment_sequence=False):
    """Update the current agent context"""
    context = {}
    if CONTEXT_FILE.exists():
        try:
            with open(CONTEXT_FILE, 'r') as f:
                context = json.load(f)
        except:
            context = {}
    
    if agent_name is not None:
        context['agent_name'] = agent_name
        context['agent_invocation_id'] = invocation_id
        context['tool_sequence_number'] = 0
    
    if increment_sequence:
        context['tool_sequence_number'] = context.get('tool_sequence_number', 0) + 1
    
    with open(CONTEXT_FILE, 'w') as f:
        json.dump(context, f)
    
    return context.get('tool_sequence_number', 0)

def log_pre_tool_use(hook_data):
    """Log PreToolUse event for any tool"""
    timestamp = datetime.now().isoformat()
    session_id = hook_data.get("session_id", "unknown")
    tool_name = hook_data.get("tool_name", "")
    tool_input = hook_data.get("tool_input", {})
    
    # Special handling for Task tool - this starts a new agent context
    if tool_name == "Task":
        # Extract agent info from Task input
        agent_name = tool_input.get("subagent_type", "unknown")
        
        # Get the next invocation ID
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT MAX(id) FROM agent_invocations 
            WHERE session_id = ? AND agent_name = ?
        ''', (session_id, agent_name))
        result = cursor.fetchone()
        invocation_id = (result[0] if result[0] else 0) + 1
        conn.close()
        
        # Update context for new agent
        update_agent_context(agent_name, invocation_id)
        
        # Log this in agent_invocations table as well (for compatibility)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO agent_invocations (
                timestamp, session_id, event_type, agent_name,
                start_time, status, raw_input
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, session_id, "tool_tracking_start", agent_name,
            timestamp, "started", json.dumps(tool_input)
        ))
        conn.commit()
        conn.close()
        
        print(f"[HOOK] Agent context started: {agent_name}", file=sys.stderr)
        return
    
    # For all other tools, log within current agent context
    agent_name, invocation_id, _ = get_current_agent_context()
    if not agent_name:
        # No active agent context, use "direct" for tools called outside agents
        agent_name = "direct"
        invocation_id = 0
    
    # Increment sequence number
    sequence_num = update_agent_context(increment_sequence=True)
    
    # Store in database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO agent_tool_uses (
            timestamp, session_id, agent_name, agent_invocation_id,
            tool_name, tool_input, start_time, status, sequence_number
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        timestamp, session_id, agent_name, invocation_id,
        tool_name, json.dumps(tool_input), timestamp, "started", sequence_num
    ))
    
    conn.commit()
    conn.close()
    
    print(f"[HOOK] Tool used by {agent_name}: {tool_name} (seq: {sequence_num})", file=sys.stderr)

def log_post_tool_use(hook_data):
    """Log PostToolUse event for any tool"""
    timestamp = datetime.now().isoformat()
    session_id = hook_data.get("session_id", "unknown")
    tool_name = hook_data.get("tool_name", "")
    tool_response = hook_data.get("tool_response", {})
    tool_error = hook_data.get("tool_error")
    
    # Special handling for Task tool - this ends agent context
    if tool_name == "Task":
        # Clear the agent context
        if CONTEXT_FILE.exists():
            os.remove(CONTEXT_FILE)
        print(f"[HOOK] Agent context ended", file=sys.stderr)
        return
    
    # For all other tools, update the most recent entry
    agent_name, invocation_id, sequence_num = get_current_agent_context()
    if not agent_name:
        agent_name = "direct"
        invocation_id = 0
    
    # Update database with completion
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Find the most recent tool use for this agent and tool
    cursor.execute('''
        SELECT id, start_time FROM agent_tool_uses
        WHERE session_id = ? AND agent_name = ? AND tool_name = ? 
        AND end_time IS NULL
        ORDER BY timestamp DESC
        LIMIT 1
    ''', (session_id, agent_name, tool_name))
    
    result = cursor.fetchone()
    if result:
        tool_use_id, start_time = result
        
        # Calculate duration
        duration = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                end_dt = datetime.fromisoformat(timestamp)
                duration = (end_dt - start_dt).total_seconds()
            except:
                pass
        
        # Determine status
        status = "error" if tool_error else "completed"
        
        # Update the record
        cursor.execute('''
            UPDATE agent_tool_uses
            SET end_time = ?, status = ?, tool_output = ?, 
                error = ?, duration_seconds = ?
            WHERE id = ?
        ''', (
            timestamp, status, json.dumps(tool_response) if tool_response else None,
            str(tool_error) if tool_error else None, duration, tool_use_id
        ))
        
        conn.commit()
    
    conn.close()
    
    print(f"[HOOK] Tool completed by {agent_name}: {tool_name} ({status})", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description='Log tool operations within agent context')
    parser.add_argument('--post', action='store_true', help='PostToolUse event')
    args = parser.parse_args()
    
    # Initialize database
    init_database()
    
    # Read hook data from stdin
    try:
        hook_data = json.load(sys.stdin)
        
        if args.post:
            log_post_tool_use(hook_data)
        else:
            log_pre_tool_use(hook_data)
            
    except Exception as e:
        print(f"[HOOK ERROR] {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()