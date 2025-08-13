#!/usr/bin/env python3
"""
Voice Notifier for Claude Code
Provides audio notifications when Claude stops or needs attention
"""

import json
import sys
import subprocess
from pathlib import Path

def speak(message):
    """Use macOS say command to speak a message"""
    try:
        subprocess.run(['say', message], check=False)
    except Exception as e:
        print(f"[VOICE ERROR] Failed to speak: {e}", file=sys.stderr)

def handle_stop(data):
    """Handle Stop event - Claude has finished"""
    speak("Claude has stopped")

def handle_notification(data):
    """Handle Notification event - Claude needs attention"""
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