#!/usr/bin/env python3
"""
Session Logger for Claude Code
Tracks session start and end events
"""

import json
import sys
import sqlite3
import subprocess
import os
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

def get_git_branch():
    """Get current git branch"""
    try:
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True, cwd=PROJECT_DIR)
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except:
        return "unknown"

def get_claude_version():
    """Get Claude Code version from environment or default"""
    return os.environ.get('CLAUDE_VERSION', 'unknown')

def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT,
            cwd TEXT,
            metadata JSON
        )
    ''')
    
    conn.commit()
    conn.close()

def log_session_start(hook_data):
    """Log SessionStart event"""
    timestamp = datetime.now().isoformat()
    session_id = hook_data.get("session_id", "unknown")
    cwd = hook_data.get("cwd", "")
    transcript_path = hook_data.get("transcript_path", "")
    source = hook_data.get("source", "")
    
    # Enhanced metadata with all available fields
    enhanced_metadata = {
        **hook_data,
        "captured_at": timestamp,
        "git_branch": get_git_branch(),
        "claude_version": get_claude_version()
    }
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO sessions (
            session_id, start_time, status, cwd, metadata
        ) VALUES (?, ?, ?, ?, ?)
    ''', (
        session_id, timestamp, "active", cwd, json.dumps(enhanced_metadata)
    ))
    
    conn.commit()
    conn.close()
    
    # Create session JSON file
    session_file = SESSIONS_DIR / f"{session_id}.json"
    session_data = [{
        "timestamp": timestamp,
        "event": "session_start",
        "cwd": cwd,
        "metadata": hook_data
    }]
    
    with open(session_file, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    print(f"[HOOK] Session started: {session_id}", file=sys.stderr)

def log_session_stop(hook_data):
    """Log Stop event (session end)"""
    timestamp = datetime.now().isoformat()
    session_id = hook_data.get("session_id", "unknown")
    transcript_path = hook_data.get("transcript_path", "")
    stop_hook_active = hook_data.get("stop_hook_active", False)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get existing metadata
    cursor.execute('SELECT metadata FROM sessions WHERE session_id = ?', (session_id,))
    result = cursor.fetchone()
    if result and result[0]:
        existing_metadata = json.loads(result[0])
        existing_metadata.update({
            "stop_hook_active": stop_hook_active,
            "transcript_path_at_stop": transcript_path,
            "end_time": timestamp
        })
    else:
        existing_metadata = hook_data
    
    # Update session with additional metadata
    cursor.execute('''
        UPDATE sessions
        SET end_time = ?, status = ?, metadata = ?
        WHERE session_id = ?
    ''', (timestamp, "completed", json.dumps(existing_metadata), session_id))
    
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
        "event": "session_stop"
    })
    
    with open(session_file, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    print(f"[HOOK] Session stopped: {session_id}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description='Log session events')
    parser.add_argument('--start', action='store_true', help='SessionStart event')
    parser.add_argument('--stop', action='store_true', help='Stop event')
    args = parser.parse_args()
    
    # Initialize database
    init_database()
    
    # Read hook data from stdin
    try:
        hook_data = json.load(sys.stdin)
        
        if args.start:
            log_session_start(hook_data)
        elif args.stop:
            log_session_stop(hook_data)
            
    except Exception as e:
        print(f"[HOOK ERROR] {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()