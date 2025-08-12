#!/usr/bin/env python3
"""
Simple monitoring script for agent workflow logs
"""

import sqlite3
from pathlib import Path
import json

# Setup paths
TOOLS_DIR = Path(__file__).parent
PROJECT_DIR = TOOLS_DIR.parent
LOGS_DIR = PROJECT_DIR / "logs"
DB_PATH = LOGS_DIR / "agent_workflow.db"
SESSIONS_DIR = LOGS_DIR / "sessions"

def monitor():
    """Show current logging status"""
    
    print("=" * 60)
    print("🔍 AGENT WORKFLOW LOGGING MONITOR")
    print("=" * 60)
    
    # Check if database exists
    if not DB_PATH.exists():
        print("❌ No database found. Hooks may not be active yet.")
        print("   Run an agent command to start logging.")
        return
    
    print("✅ Database found at:", DB_PATH)
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check sessions
    print("\n📊 SESSIONS:")
    print("-" * 40)
    cursor.execute("SELECT session_id, start_time, end_time, status FROM sessions ORDER BY start_time DESC LIMIT 5")
    sessions = cursor.fetchall()
    
    if sessions:
        for session_id, start, end, status in sessions:
            duration = "ongoing" if not end else "completed"
            print(f"  {session_id[:12]}... | {status:10} | {duration}")
    else:
        print("  No sessions logged yet")
    
    # Check agent invocations
    print("\n🤖 RECENT AGENT INVOCATIONS:")
    print("-" * 40)
    cursor.execute("SELECT agent_name, phase, timestamp, status FROM agent_invocations ORDER BY timestamp DESC LIMIT 10")
    invocations = cursor.fetchall()
    
    if invocations:
        for agent, phase, timestamp, status in invocations:
            if agent and agent != "unknown":
                print(f"  {agent:20} | {phase or 'N/A':12} | {status or 'pending'}")
    else:
        print("  No agent invocations logged yet")
        print("  Try running: /dev-orchestrator <ticket-id>")
        print("  Or: /analyst")
    
    # Check for recent hooks activity
    print("\n📝 SESSION FILES:")
    print("-" * 40)
    if SESSIONS_DIR.exists():
        session_files = list(SESSIONS_DIR.glob("*.json"))
        print(f"  Found {len(session_files)} session file(s)")
        
        # Show latest session file content
        if session_files:
            latest = max(session_files, key=lambda p: p.stat().st_mtime)
            print(f"  Latest: {latest.name}")
            
            with open(latest, 'r') as f:
                data = json.load(f)
                print(f"  Events logged: {len(data)}")
                if data:
                    print(f"  Last event: {data[-1].get('event', 'unknown')}")
    
    # Hook status
    print("\n⚙️  HOOK STATUS:")
    print("-" * 40)
    # Check if hooks are installed in user's Claude settings
    user_settings = Path.home() / ".claude" / "settings.json"
    if user_settings.exists():
        with open(user_settings, 'r') as f:
            settings = json.load(f)
            hooks = settings.get('hooks', {})
            # Check if our hooks are installed
            if any('log_agent_invocation' in str(hook) for hook in str(hooks).split()):
                print("  ✅ Logging hooks installed in ~/.claude/settings.json")
                print(f"  Active hook types: {', '.join(hooks.keys())}")
            else:
                print("  ⚠️  Claude settings found but logging hooks not installed")
                print("  Run ./install-logging.sh to install")
    else:
        print("  ❌ No ~/.claude/settings.json found")
        print("  Claude Code may not be configured")
    
    conn.close()
    
    print("\n💡 TIP: Hooks print to stderr, so you'll see [HOOK] messages")
    print("   when agents are invoked (e.g., '[HOOK] Agent invoked: jira-analyst')")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    monitor()