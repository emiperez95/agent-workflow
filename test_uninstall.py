#!/usr/bin/env python3
"""
Test script for uninstall functionality
Tests that the uninstall script correctly removes only our hooks
while preserving other hooks from different projects
"""

import json
import sys
import tempfile
import shutil
from pathlib import Path

# Test data - simulates a settings.json with mixed hooks
TEST_SETTINGS = {
    "hooks": {
        "SessionStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 /Users/emilianoperez/Projects/00-Personal/agent-workflow/hooks/log_session.py --start"
                    }
                ]
            },
            {
                "hooks": [
                    {
                        "type": "command", 
                        "command": "echo 'Another project hook that should remain'"
                    }
                ]
            }
        ],
        "PreToolUse": [
            {
                "matcher": "Task",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 /Users/emilianoperez/Projects/00-Personal/agent-workflow/hooks/log_agent_invocation.py"
                    }
                ]
            },
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 /different/project/hook.py"
                    }
                ]
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Task",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 /Users/emilianoperez/Projects/00-Personal/agent-workflow/hooks/log_agent_invocation.py --post"
                    }
                ]
            }
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 /Users/emilianoperez/Projects/00-Personal/agent-workflow/hooks/log_session.py --stop"
                    }
                ]
            }
        ]
    },
    "other_setting": "should remain unchanged"
}

def test_uninstall():
    """Test the uninstall logic"""
    
    # Create a copy of test settings
    settings = json.loads(json.dumps(TEST_SETTINGS))
    
    print("BEFORE UNINSTALL:")
    print(json.dumps(settings, indent=2))
    print("\n" + "="*60 + "\n")
    
    # Uninstall logic (copied from uninstall script)
    project_dir = "/Users/emilianoperez/Projects/00-Personal/agent-workflow"
    
    # Commands to remove
    our_hook_patterns = [
        f"python3 {project_dir}/hooks/log_session.py",
        f"python3 {project_dir}/hooks/log_agent_invocation.py"
    ]
    
    hooks_removed = False
    
    # Process each hook event
    for event in list(settings['hooks'].keys()):
        if event not in settings['hooks']:
            continue
        
        # Filter out our hooks
        filtered_config = []
        for item in settings['hooks'][event]:
            if 'hooks' in item:
                # Filter hooks within this item
                filtered_hooks = []
                for hook in item['hooks']:
                    if 'command' in hook:
                        # Check if this is one of our commands
                        is_ours = any(pattern in hook['command'] for pattern in our_hook_patterns)
                        if is_ours:
                            print(f"Removing {event} hook: {hook['command'][:50]}...")
                            hooks_removed = True
                        else:
                            filtered_hooks.append(hook)
                    else:
                        filtered_hooks.append(hook)
                
                # Update the item with filtered hooks
                if filtered_hooks:
                    item['hooks'] = filtered_hooks
                    filtered_config.append(item)
                elif 'matcher' not in item:
                    # If no hooks left and no matcher, skip this item entirely
                    pass
            else:
                filtered_config.append(item)
        
        # Update or remove the event
        if filtered_config:
            settings['hooks'][event] = filtered_config
        else:
            # Remove the event entirely if no hooks left
            del settings['hooks'][event]
            print(f"Removed empty {event} event")
    
    # Clean up empty hooks section
    if 'hooks' in settings and not settings['hooks']:
        del settings['hooks']
        print("Removed empty hooks section")
    
    print("\nAFTER UNINSTALL:")
    print(json.dumps(settings, indent=2))
    
    # Verify results
    print("\n" + "="*60)
    print("VERIFICATION:")
    
    # Check that our hooks are gone
    if 'hooks' in settings:
        for event, config in settings['hooks'].items():
            for item in config:
                if 'hooks' in item:
                    for hook in item['hooks']:
                        if 'command' in hook:
                            for pattern in our_hook_patterns:
                                if pattern in hook['command']:
                                    print(f"❌ FAILED: Found our hook still present: {hook['command']}")
                                    return False
    
    # Check that other hooks remain
    if 'hooks' not in settings or 'SessionStart' not in settings['hooks']:
        print("❌ FAILED: Other project hooks were removed")
        return False
    
    # Check that other project's Bash hook remains
    bash_hook_found = False
    if 'hooks' in settings and 'PreToolUse' in settings['hooks']:
        for item in settings['hooks']['PreToolUse']:
            if item.get('matcher') == 'Bash':
                bash_hook_found = True
                break
    
    if not bash_hook_found:
        print("❌ FAILED: Other project's Bash hook was removed")
        return False
    
    # Check that other settings remain
    if settings.get('other_setting') != 'should remain unchanged':
        print("❌ FAILED: Other settings were modified")
        return False
    
    print("✅ All our hooks removed")
    print("✅ Other project hooks preserved")
    print("✅ Other settings unchanged")
    print("\n✅ TEST PASSED!")
    return True

if __name__ == "__main__":
    success = test_uninstall()
    sys.exit(0 if success else 1)