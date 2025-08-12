#!/usr/bin/env python3
"""
Live monitoring tool for agent workflow logs
Works like 'tail -f' to show real-time agent activity
"""

import sqlite3
import json
import time
import sys
from pathlib import Path
from datetime import datetime
import argparse

# Setup paths
TOOLS_DIR = Path(__file__).parent
PROJECT_DIR = TOOLS_DIR.parent
LOGS_DIR = PROJECT_DIR / "logs"
DB_PATH = LOGS_DIR / "agent_workflow.db"
SESSIONS_DIR = LOGS_DIR / "sessions"

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def get_latest_session():
    """Get the most recent session ID"""
    if not DB_PATH.exists():
        return None
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT session_id FROM sessions ORDER BY start_time DESC LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def format_event(event):
    """Format an event for display"""
    event_type = event.get('event', 'unknown')
    timestamp = event.get('timestamp', '')
    
    # Extract time portion
    if 'T' in timestamp:
        time_str = timestamp.split('T')[1].split('.')[0]
    else:
        time_str = timestamp
    
    # Color-code based on event type
    if 'start' in event_type:
        color = Colors.GREEN
        icon = "▶️ "
    elif 'complete' in event_type or 'stop' in event_type:
        color = Colors.BLUE
        icon = "✅"
    else:
        color = Colors.YELLOW
        icon = "⚡"
    
    # Build output string
    output = f"{color}[{time_str}] {icon} {event_type}{Colors.END}"
    
    # Add agent details if present
    agent = event.get('agent', {})
    if agent and isinstance(agent, dict):
        agent_name = agent.get('name', '')
        agent_type = agent.get('type', '')
        if agent_name:
            output += f" - {Colors.BOLD}{agent_name}{Colors.END}"
            if agent_type:
                output += f" ({agent_type})"
    
    # Add execution time for completions
    if event_type == 'agent_invocation_complete':
        raw_output = event.get('raw_output', {})
        if isinstance(raw_output, dict):
            duration = raw_output.get('totalDurationMs', 0)
            tokens = raw_output.get('totalTokens', 0)
            if duration:
                output += f" | {Colors.CYAN}{duration/1000:.2f}s{Colors.END}"
            if tokens:
                output += f" | {Colors.YELLOW}{tokens} tokens{Colors.END}"
    
    # Add snippet of prompt for start events
    if event_type == 'agent_invocation_start' and agent:
        prompt = agent.get('prompt', '')
        if prompt:
            snippet = prompt[:60] + '...' if len(prompt) > 60 else prompt
            output += f"\n    └─ {Colors.CYAN}\"{snippet}\"{Colors.END}"
    
    return output

def tail_session(session_id, follow=True, lines=10):
    """Tail a specific session's log file"""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    
    if not session_file.exists():
        print(f"❌ Session file not found: {session_id}")
        return
    
    print(f"{Colors.HEADER}📡 LIVE AGENT MONITORING{Colors.END}")
    print(f"{Colors.HEADER}Session: {session_id[:12]}...{Colors.END}")
    print("=" * 60)
    
    last_size = 0
    last_events_count = 0
    
    try:
        while True:
            # Check if file has changed
            current_size = session_file.stat().st_size
            
            if current_size != last_size:
                # File has changed, read it
                with open(session_file, 'r') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        # File might be in the middle of being written
                        time.sleep(0.1)
                        continue
                
                # Show new events
                if len(data) > last_events_count:
                    # Initial load - show last N events
                    if last_events_count == 0:
                        start_index = max(0, len(data) - lines)
                        if start_index > 0:
                            print(f"... showing last {lines} events ...\n")
                    else:
                        start_index = last_events_count
                    
                    for event in data[start_index:]:
                        print(format_event(event))
                    
                    last_events_count = len(data)
                
                last_size = current_size
            
            if not follow:
                break
            
            # Don't auto-stop on session_stop events since they can be duplicated
            # User can press Ctrl+C to stop monitoring
            
            time.sleep(0.5)  # Poll every 500ms
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Stopped monitoring{Colors.END}")

def tail_all(follow=True, lines=10):
    """Monitor all active sessions"""
    print(f"{Colors.HEADER}📡 MONITORING ALL SESSIONS{Colors.END}")
    print("=" * 60)
    
    seen_events = set()
    
    try:
        while True:
            # Find all session files
            if SESSIONS_DIR.exists():
                session_files = sorted(SESSIONS_DIR.glob("*.json"), 
                                     key=lambda p: p.stat().st_mtime, 
                                     reverse=True)
                
                for session_file in session_files[:3]:  # Monitor last 3 sessions
                    with open(session_file, 'r') as f:
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            continue
                    
                    for event in data:
                        # Create unique event ID
                        event_id = f"{session_file.stem}_{event.get('timestamp', '')}"
                        
                        if event_id not in seen_events:
                            seen_events.add(event_id)
                            
                            # Only show if recent (for initial load)
                            if len(seen_events) <= lines or follow:
                                session_short = session_file.stem[:8]
                                output = format_event(event)
                                print(f"[{session_short}] {output}")
            
            if not follow:
                break
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Stopped monitoring{Colors.END}")

def watch_live():
    """Simple live view showing current activity"""
    print(f"{Colors.HEADER}🔴 LIVE AGENT ACTIVITY{Colors.END}")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Get or start with latest session
    session_id = get_latest_session()
    if session_id:
        print(f"Monitoring session: {session_id[:12]}...\n")
        tail_session(session_id, follow=True, lines=5)
    else:
        print("No active sessions. Waiting for activity...")
        # Could implement watching for new sessions here

def main():
    parser = argparse.ArgumentParser(description='Live monitoring of agent logs')
    parser.add_argument('--session', help='Specific session ID to monitor')
    parser.add_argument('--all', action='store_true', help='Monitor all sessions')
    parser.add_argument('-f', '--follow', action='store_true', help='Follow mode (like tail -f)')
    parser.add_argument('-n', '--lines', type=int, default=10, help='Number of initial lines to show')
    args = parser.parse_args()
    
    if not LOGS_DIR.exists():
        print("❌ No logs directory found. Hooks may not be configured.")
        print("   Check that .claude/settings.json exists")
        return
    
    if args.session:
        tail_session(args.session, follow=args.follow, lines=args.lines)
    elif args.all:
        tail_all(follow=args.follow, lines=args.lines)
    else:
        # Default: watch latest session live
        watch_live()

if __name__ == "__main__":
    main()