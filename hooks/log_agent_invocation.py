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
    try:
        timestamp = datetime.now().isoformat()
        session_id = hook_data.get("session_id", "unknown")
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})
        
        if tool_name == "Task":
            agent_info = extract_agent_info(tool_input)
            
            # Store in database and get the ID for efficient lookup later
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # Safely serialize tool_input
                try:
                    raw_input_json = json.dumps(tool_input)
                except (TypeError, ValueError) as e:
                    raw_input_json = json.dumps({"error": f"Failed to serialize: {str(e)}"})
                
                cursor.execute('''
                    INSERT INTO agent_invocations (
                        timestamp, session_id, event_type, phase, agent_name,
                        agent_type, prompt, start_time, status, raw_input
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp, session_id, "pre_invocation", agent_info["type"],
                    agent_info["name"], agent_info["type"], agent_info["prompt"][:5000],  # Limit prompt length
                    timestamp, "started", raw_input_json
                ))
                
                # Store the invocation ID for fast lookup in post_tool_use
                invocation_id = cursor.lastrowid
                
                conn.commit()
                conn.close()
            except sqlite3.Error as e:
                print(f"[HOOK WARNING] Database error: {str(e)}", file=sys.stderr)
                invocation_id = None
            
            # Store invocation ID in a temporary mapping file for the session
            if invocation_id:
                try:
                    invocation_map_file = SESSIONS_DIR / f"{session_id}_invocations.json"
                    invocation_map = {}
                    if invocation_map_file.exists():
                        try:
                            with open(invocation_map_file, 'r') as f:
                                invocation_map = json.load(f)
                        except (json.JSONDecodeError, IOError):
                            invocation_map = {}
                    
                    # Use agent_name and timestamp as key for mapping
                    map_key = f"{agent_info['name']}_{timestamp}"
                    invocation_map[map_key] = invocation_id
                    
                    with open(invocation_map_file, 'w') as f:
                        json.dump(invocation_map, f)
                except Exception as e:
                    print(f"[HOOK WARNING] Failed to save invocation mapping: {str(e)}", file=sys.stderr)
            
            # Also save to session JSON file
            try:
                session_file = SESSIONS_DIR / f"{session_id}.json"
                session_data = []
                if session_file.exists():
                    try:
                        with open(session_file, 'r') as f:
                            session_data = json.load(f)
                    except (json.JSONDecodeError, IOError):
                        session_data = []
                
                session_data.append({
                    "timestamp": timestamp,
                    "event": "agent_invocation_start",
                    "agent": agent_info,
                    "raw_input": tool_input
                })
                
                with open(session_file, 'w') as f:
                    json.dump(session_data, f, indent=2, default=str)  # Use default=str for non-serializable objects
            except Exception as e:
                print(f"[HOOK WARNING] Failed to save session data: {str(e)}", file=sys.stderr)
            
            # Print to stderr for debugging
            print(f"[HOOK] Agent invoked: {agent_info['name']} ({agent_info['type']})", file=sys.stderr)
    except Exception as e:
        print(f"[HOOK WARNING] Error in log_pre_tool_use: {str(e)}", file=sys.stderr)

def log_post_tool_use(hook_data):
    """Log PostToolUse event for Task tool"""
    try:
        timestamp = datetime.now().isoformat()
        session_id = hook_data.get("session_id", "unknown")
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})
        tool_response = hook_data.get("tool_response", {})
        transcript_path = hook_data.get("transcript_path", "")
        
        if tool_name == "Task":
            agent_info = extract_agent_info(tool_input)
            
            # Update database with completion
            try:
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
                    try:
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
                    except (json.JSONDecodeError, IOError) as e:
                        print(f"[HOOK WARNING] Failed to read invocation map: {str(e)}", file=sys.stderr)
                
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
                    
                    # Safely serialize tool_response
                    try:
                        raw_output_json = json.dumps(tool_response)
                    except (TypeError, ValueError) as e:
                        raw_output_json = json.dumps({"error": f"Failed to serialize: {str(e)}"})
                    
                    # Update with all new fields (single UPDATE query instead of SELECT+UPDATE)
                    cursor.execute('''
                        UPDATE agent_invocations
                        SET end_time = ?, status = ?, raw_output = ?, 
                            duration_seconds = ?, model = ?
                        WHERE id = ?
                    ''', (
                        timestamp, "completed", raw_output_json,
                        duration_seconds, model, invocation_id
                    ))
                
                conn.commit()
                conn.close()
            except sqlite3.Error as e:
                print(f"[HOOK WARNING] Database error in post_tool_use: {str(e)}", file=sys.stderr)
            
            # Update session JSON
            try:
                session_file = SESSIONS_DIR / f"{session_id}.json"
                session_data = []
                if session_file.exists():
                    try:
                        with open(session_file, 'r') as f:
                            session_data = json.load(f)
                    except (json.JSONDecodeError, IOError):
                        session_data = []
                
                session_data.append({
                    "timestamp": timestamp,
                    "event": "agent_invocation_complete",
                    "agent": agent_info,
                    "raw_output": tool_response
                })
                
                with open(session_file, 'w') as f:
                    json.dump(session_data, f, indent=2, default=str)  # Use default=str for non-serializable objects
            except Exception as e:
                print(f"[HOOK WARNING] Failed to save session data in post_tool_use: {str(e)}", file=sys.stderr)
            
            print(f"[HOOK] Agent completed: {agent_info['name']}", file=sys.stderr)
    except Exception as e:
        print(f"[HOOK WARNING] Error in log_post_tool_use: {str(e)}", file=sys.stderr)

def log_subagent_stop(hook_data):
    """Log SubagentStop event"""
    try:
        timestamp = datetime.now().isoformat()
        session_id = hook_data.get("session_id", "unknown")
        
        # Log subagent completion
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO agent_invocations (
                    timestamp, session_id, event_type, status
                ) VALUES (?, ?, ?, ?)
            ''', (timestamp, session_id, "subagent_stop", "completed"))
            
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print(f"[HOOK WARNING] Database error in log_subagent_stop: {str(e)}", file=sys.stderr)
        
        print(f"[HOOK] Subagent stopped", file=sys.stderr)
    except Exception as e:
        print(f"[HOOK WARNING] Error in log_subagent_stop: {str(e)}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description='Log agent invocations')
    parser.add_argument('--post', action='store_true', help='PostToolUse event')
    parser.add_argument('--subagent-stop', action='store_true', help='SubagentStop event')
    args = parser.parse_args()
    
    # Initialize database
    init_database()
    
    # Read hook data from stdin
    try:
        # Read raw input for debugging
        raw_input = sys.stdin.read()
        
        # Debug: Save raw input when JSON parsing fails
        debug_file = LOGS_DIR / "hook_debug.log"
        
        try:
            # Attempt to parse JSON
            hook_data = json.loads(raw_input)
        except json.JSONDecodeError as je:
            # Log the problematic input for debugging
            timestamp = datetime.now().isoformat()
            with open(debug_file, 'a') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"JSON Parse Error at {timestamp}\n")
                f.write(f"Error: {str(je)}\n")
                f.write(f"Error Position: Line {je.lineno}, Column {je.colno}, Char {je.pos}\n")
                f.write(f"Raw input length: {len(raw_input)} characters\n")
                f.write(f"First 500 chars: {raw_input[:500]}\n")
                f.write(f"Last 500 chars: {raw_input[-500:]}\n")
                
                # Try to identify the problematic section
                if je.pos and je.pos < len(raw_input):
                    start = max(0, je.pos - 100)
                    end = min(len(raw_input), je.pos + 100)
                    f.write(f"Context around error position:\n")
                    f.write(f"...{raw_input[start:end]}...\n")
                    f.write(f"{'='*60}\n")
            
            print(f"[HOOK ERROR] JSON parsing failed: {str(je)}", file=sys.stderr)
            print(f"[HOOK ERROR] Debug info saved to {debug_file}", file=sys.stderr)
            # Exit with 0 to not block the operation
            sys.exit(0)
        
        # Process the hook data
        try:
            if args.post:
                log_post_tool_use(hook_data)
            elif args.subagent_stop:
                log_subagent_stop(hook_data)
            else:
                log_pre_tool_use(hook_data)
        except Exception as e:
            # Log processing errors but don't fail
            print(f"[HOOK WARNING] Processing error (continuing): {str(e)}", file=sys.stderr)
            with open(debug_file, 'a') as f:
                f.write(f"\nProcessing Error at {datetime.now().isoformat()}: {str(e)}\n")
            
    except Exception as e:
        # Catch any other unexpected errors
        print(f"[HOOK WARNING] Unexpected error (continuing): {str(e)}", file=sys.stderr)
        # Exit with 0 to not block the operation
        sys.exit(0)
    
    sys.exit(0)

if __name__ == "__main__":
    main()