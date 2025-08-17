#!/usr/bin/env python3
"""
Agent Invocation Logger for Claude Code
Tracks all Task tool invocations to understand agent workflow patterns
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
SESSIONS_DIR = LOGS_DIR / "sessions"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)

def cleanup_old_mappings():
    """Clean up old invocation mapping files (older than 24 hours)"""
    try:
        import time
        current_time = time.time()
        for mapping_file in SESSIONS_DIR.glob("*_invocations.json"):
            if mapping_file.stat().st_mtime < current_time - 86400:  # 24 hours
                mapping_file.unlink()
    except Exception:
        pass  # Ignore cleanup errors

def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clean up old mapping files periodically
    cleanup_old_mappings()
    
    # Create tables if they don't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_invocations (
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
            raw_output JSON,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tool_uses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP,
            session_id TEXT,
            tool_name TEXT,
            tool_input JSON,
            tool_output JSON,
            duration_seconds REAL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def extract_agent_info(tool_input):
    """Extract agent information from Task tool input"""
    agent_info = {
        "name": "unknown",
        "type": "unknown",
        "prompt": "",
        "ticket_id": None
    }
    
    if isinstance(tool_input, dict):
        # Extract subagent_type if present
        agent_info["name"] = tool_input.get("subagent_type", "unknown")
        agent_info["prompt"] = tool_input.get("prompt", "")
        
        # Try to extract ticket ID from prompt
        if "ticket" in agent_info["prompt"].lower():
            import re
            ticket_match = re.search(r'\b[A-Z]+-\d+\b', agent_info["prompt"])
            if ticket_match:
                agent_info["ticket_id"] = ticket_match.group()
        
        # Determine agent type/phase based on agent name
        agent_name = agent_info["name"]
        if agent_name in ["jira-analyst", "context-analyzer", "requirements-clarifier"]:
            agent_info["type"] = "requirements"
        elif agent_name in ["agent-discoverer", "story-analyzer", "architect", "task-planner"]:
            agent_info["type"] = "planning"
        elif agent_name in ["backend-developer", "frontend-developer", "database-developer", "test-developer"]:
            agent_info["type"] = "development"
        elif agent_name in ["performance-reviewer", "security-reviewer", "maintainability-reviewer", "test-validator"]:
            agent_info["type"] = "review"
        elif agent_name in ["documentation-generator", "changelog-writer", "pr-creator"]:
            agent_info["type"] = "finalization"
    
    return agent_info

def log_pre_tool_use(hook_data):
    """Log PreToolUse event for Task tool"""
    timestamp = datetime.now().isoformat()
    session_id = hook_data.get("session_id", "unknown")
    tool_name = hook_data.get("tool_name", "")
    tool_input = hook_data.get("tool_input", {})
    
    if tool_name == "Task":
        agent_info = extract_agent_info(tool_input)
        
        # Store in database and get the ID for efficient lookup later
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO agent_invocations (
                timestamp, session_id, event_type, phase, agent_name,
                agent_type, prompt, start_time, status, raw_input
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, session_id, "pre_invocation", agent_info["type"],
            agent_info["name"], agent_info["type"], agent_info["prompt"],
            timestamp, "started", json.dumps(tool_input)
        ))
        
        # Store the invocation ID for fast lookup in post_tool_use
        invocation_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        # Store invocation ID in a temporary mapping file for the session
        # This avoids the N+1 query problem
        invocation_map_file = SESSIONS_DIR / f"{session_id}_invocations.json"
        invocation_map = {}
        if invocation_map_file.exists():
            with open(invocation_map_file, 'r') as f:
                invocation_map = json.load(f)
        
        # Use agent_name and timestamp as key for mapping
        map_key = f"{agent_info['name']}_{timestamp}"
        invocation_map[map_key] = invocation_id
        
        with open(invocation_map_file, 'w') as f:
            json.dump(invocation_map, f)
        
        # Also save to session JSON file
        session_file = SESSIONS_DIR / f"{session_id}.json"
        session_data = []
        if session_file.exists():
            with open(session_file, 'r') as f:
                session_data = json.load(f)
        
        session_data.append({
            "timestamp": timestamp,
            "event": "agent_invocation_start",
            "agent": agent_info,
            "raw_input": tool_input
        })
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        # Print to stderr for debugging
        print(f"[HOOK] Agent invoked: {agent_info['name']} ({agent_info['type']})", file=sys.stderr)

def log_post_tool_use(hook_data):
    """Log PostToolUse event for Task tool"""
    timestamp = datetime.now().isoformat()
    session_id = hook_data.get("session_id", "unknown")
    tool_name = hook_data.get("tool_name", "")
    tool_input = hook_data.get("tool_input", {})
    tool_response = hook_data.get("tool_response", {})
    transcript_path = hook_data.get("transcript_path", "")
    
    if tool_name == "Task":
        agent_info = extract_agent_info(tool_input)
        
        # Update database with completion
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Extract performance metrics from response
        usage_info = tool_response.get("usage", {})
        total_tokens = tool_response.get("totalTokens", 0)
        duration_ms = tool_response.get("totalDurationMs", 0)
        
        # Calculate duration in seconds
        duration_seconds = duration_ms / 1000.0 if duration_ms else None
        
        # Extract model info if available
        model = usage_info.get("service_tier", "")
        
        # Try to get invocation ID from mapping file first (avoids N+1 query)
        invocation_id = None
        start_time = None
        invocation_map_file = SESSIONS_DIR / f"{session_id}_invocations.json"
        
        if invocation_map_file.exists():
            with open(invocation_map_file, 'r') as f:
                invocation_map = json.load(f)
            
            # Find the most recent invocation ID for this agent
            for key in sorted(invocation_map.keys(), reverse=True):
                if key.startswith(f"{agent_info['name']}_"):
                    invocation_id = invocation_map[key]
                    # Clean up used mapping
                    del invocation_map[key]
                    with open(invocation_map_file, 'w') as f:
                        json.dump(invocation_map, f)
                    break
        
        # Fallback to query if mapping not found (backward compatibility)
        if not invocation_id:
            cursor.execute('''
                SELECT id, start_time FROM agent_invocations
                WHERE session_id = ? AND agent_name = ? AND end_time IS NULL
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (session_id, agent_info["name"]))
            
            result = cursor.fetchone()
            if result:
                invocation_id, start_time = result
        else:
            # Get start_time for duration calculation
            cursor.execute('SELECT start_time FROM agent_invocations WHERE id = ?', (invocation_id,))
            result = cursor.fetchone()
            if result:
                start_time = result[0]
        
        if invocation_id:
            # Calculate duration if not provided
            if not duration_seconds and start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time)
                    end_dt = datetime.fromisoformat(timestamp)
                    duration_seconds = (end_dt - start_dt).total_seconds()
                except:
                    pass
            
            # Update with all new fields (single UPDATE query instead of SELECT+UPDATE)
            cursor.execute('''
                UPDATE agent_invocations
                SET end_time = ?, status = ?, raw_output = ?, 
                    duration_seconds = ?, model = ?
                WHERE id = ?
            ''', (
                timestamp, "completed", json.dumps(tool_response),
                duration_seconds, model, invocation_id
            ))
        
        conn.commit()
        conn.close()
        
        # Update session JSON
        session_file = SESSIONS_DIR / f"{session_id}.json"
        session_data = []
        if session_file.exists():
            with open(session_file, 'r') as f:
                session_data = json.load(f)
        
        session_data.append({
            "timestamp": timestamp,
            "event": "agent_invocation_complete",
            "agent": agent_info,
            "raw_output": tool_response
        })
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        print(f"[HOOK] Agent completed: {agent_info['name']}", file=sys.stderr)

def log_subagent_stop(hook_data):
    """Log SubagentStop event"""
    timestamp = datetime.now().isoformat()
    session_id = hook_data.get("session_id", "unknown")
    
    # Log subagent completion
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO agent_invocations (
            timestamp, session_id, event_type, status
        ) VALUES (?, ?, ?, ?)
    ''', (timestamp, session_id, "subagent_stop", "completed"))
    
    conn.commit()
    conn.close()
    
    print(f"[HOOK] Subagent stopped", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description='Log agent invocations')
    parser.add_argument('--post', action='store_true', help='PostToolUse event')
    parser.add_argument('--subagent-stop', action='store_true', help='SubagentStop event')
    args = parser.parse_args()
    
    # Initialize database
    init_database()
    
    # Read hook data from stdin
    try:
        hook_data = json.load(sys.stdin)
        
        if args.post:
            log_post_tool_use(hook_data)
        elif args.subagent_stop:
            log_subagent_stop(hook_data)
        else:
            log_pre_tool_use(hook_data)
            
    except Exception as e:
        print(f"[HOOK ERROR] {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()