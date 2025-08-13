#!/bin/bash

# Uninstall Agent Workflow Logging System
# This script removes the logging hooks from Claude Code settings

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🗑️  Uninstalling Agent Workflow Logging System"
echo "============================================="

# Get the absolute path to this project
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Project directory: $PROJECT_DIR"

# Check if Claude settings exist
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
if [ ! -f "$CLAUDE_SETTINGS" ]; then
    echo -e "${YELLOW}No Claude settings file found. Nothing to uninstall.${NC}"
    exit 0
fi

# Create a Python script to remove our hooks
cat > /tmp/uninstall_claude_logging.py << EOF
#!/usr/bin/env python3
import json
import sys

settings_file = "$CLAUDE_SETTINGS"
project_dir = "$PROJECT_DIR"

# Read existing settings
try:
    with open(settings_file, 'r') as f:
        settings = json.load(f)
except Exception as e:
    print(f"❌ Error reading settings: {e}")
    sys.exit(1)

# Check if hooks section exists
if 'hooks' not in settings:
    print("No hooks found in settings. Nothing to uninstall.")
    sys.exit(0)

# Commands to remove (identify our hooks by the project path)
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
        # Check if this item contains our hooks
        keep_item = True
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
                keep_item = False
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

# Write updated settings
try:
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    
    if hooks_removed:
        print("✅ Logging hooks removed successfully")
    else:
        print("No logging hooks found for this project")
except Exception as e:
    print(f"❌ Error writing settings: {e}")
    sys.exit(1)
EOF

# Run the Python script to remove hooks
echo -e "${GREEN}Removing logging hooks from Claude settings...${NC}"
python3 /tmp/uninstall_claude_logging.py

# Clean up
rm /tmp/uninstall_claude_logging.py

# Check for global symlinks
echo ""
echo -e "${GREEN}Checking for global tool symlinks...${NC}"
REMOVED_SYMLINKS=false
for tool in analyze_workflow monitor query_logs tail_logs visualize_flow; do
    SYMLINK="/usr/local/bin/agent-${tool}"
    if [ -L "$SYMLINK" ]; then
        # Check if symlink points to our project
        LINK_TARGET=$(readlink "$SYMLINK")
        if [[ "$LINK_TARGET" == "$PROJECT_DIR"* ]]; then
            echo -e "${YELLOW}Found symlink: $SYMLINK${NC}"
            read -p "Remove this symlink? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                sudo rm "$SYMLINK"
                echo -e "${GREEN}  Removed: agent-${tool}${NC}"
                REMOVED_SYMLINKS=true
            fi
        fi
    fi
done

# Summary
echo ""
echo -e "${GREEN}✅ Uninstall complete!${NC}"
echo ""
echo "The following has been removed:"
echo "  • Logging hooks from ~/.claude/settings.json"
if [ "$REMOVED_SYMLINKS" = true ]; then
    echo "  • Global tool symlinks from /usr/local/bin"
fi
echo ""
echo "Note: The following remain (you can delete manually if desired):"
echo "  • Log files in: $PROJECT_DIR/logs/"
echo "  • Hook scripts in: $PROJECT_DIR/hooks/"
echo "  • Analysis tools in: $PROJECT_DIR/tools/"
echo ""
echo -e "${YELLOW}⚠️  Restart Claude Code for changes to take effect${NC}"