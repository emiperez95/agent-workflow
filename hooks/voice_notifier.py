#!/usr/bin/env python3
"""
Voice Notifier for Claude Code
Provides audio notifications when Claude stops or needs attention
"""

import json
import sys
import subprocess
import os
from pathlib import Path

def get_tmux_session_index():
    """Get the current tmux session index number"""
    # Check if we're in a tmux session
    if 'TMUX' in os.environ:
        try:
            # Get session ID (format: $N where N is the index)
            result = subprocess.run(
                ['tmux', 'display-message', '-p', '#{session_id}'],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                session_id = result.stdout.strip()
                # Extract the number after the $
                if session_id.startswith('$'):
                    return session_id[1:]
        except Exception:
            pass
    return None

def speak(message):
    """Use macOS say command to speak a message"""
    try:
        subprocess.run(['say', message], check=False)
    except Exception as e:
        print(f"[VOICE ERROR] Failed to speak: {e}", file=sys.stderr)

def handle_stop(data):
    """Handle Stop event - Claude has finished"""
    session_index = get_tmux_session_index()
    if session_index:
        speak(f"Claude has stopped in session {session_index}")
    else:
        speak("Claude has stopped")

def handle_notification(data):
    """Handle Notification event - Claude needs attention"""
    session_index = get_tmux_session_index()
    if session_index:
        speak(f"Claude needs your attention in session {session_index}")
    else:
        speak("Claude needs your attention")

def main():
    try:
        # Read hook data from stdin
        hook_data = json.load(sys.stdin)
        
        # Get event type from command line argument if provided
        event_type = sys.argv[1] if len(sys.argv) > 1 else "unknown"
        
        if event_type == "stop":
            handle_stop(hook_data)
        elif event_type == "notification":
            handle_notification(hook_data)
            
    except Exception as e:
        print(f"[VOICE ERROR] {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()