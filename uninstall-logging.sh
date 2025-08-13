#!/bin/bash

# Uninstall Agent Workflow Hooks
# This script removes hooks from Claude Code settings

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the absolute path to this project
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Parse command line arguments
UNINSTALL_LOGGING=false
UNINSTALL_VOICE=false
UNINSTALL_ALL=false

show_help() {
    echo ""
    echo -e "${BLUE}Agent Workflow Hook Uninstaller${NC}"
    echo "================================"
    echo ""
    echo "This script removes Claude Code hooks for this project."
    echo ""
    echo -e "${GREEN}Usage:${NC}"
    echo "  ./uninstall-logging.sh [OPTIONS]"
    echo ""
    echo -e "${GREEN}Options:${NC}"
    echo "  -l, --logging     Remove agent logging hooks"
    echo "                    Removes logging of agent invocations and sessions"
    echo ""
    echo "  -v, --voice       Remove voice notification hooks"
    echo "                    Removes voice alerts for Claude events"
    echo ""
    echo "  -a, --all         Remove all hooks"
    echo ""
    echo "  -h, --help        Show this help message"
    echo ""
    echo -e "${GREEN}Examples:${NC}"
    echo "  ./uninstall-logging.sh --logging    # Remove only logging"
    echo "  ./uninstall-logging.sh --voice      # Remove only voice notifications"
    echo "  ./uninstall-logging.sh --all        # Remove everything"
    echo "  ./uninstall-logging.sh -l -v        # Remove both logging and voice"
    echo ""
    echo -e "${YELLOW}Note:${NC} You'll need to restart Claude Code after uninstallation"
    echo ""
}

# Parse arguments
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--logging)
            UNINSTALL_LOGGING=true
            shift
            ;;
        -v|--voice)
            UNINSTALL_VOICE=true
            shift
            ;;
        -a|--all)
            UNINSTALL_ALL=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# If --all is specified, enable everything
if [ "$UNINSTALL_ALL" = true ]; then
    UNINSTALL_LOGGING=true
    UNINSTALL_VOICE=true
fi

# Check if at least one feature is selected
if [ "$UNINSTALL_LOGGING" = false ] && [ "$UNINSTALL_VOICE" = false ]; then
    echo -e "${RED}Error: No features selected for removal${NC}"
    show_help
    exit 1
fi

echo ""
echo "🗑️  Uninstalling Agent Workflow Hooks"
echo "====================================="
echo "Project directory: $PROJECT_DIR"
echo ""

# Display what will be uninstalled
echo -e "${GREEN}Features to remove:${NC}"
[ "$UNINSTALL_LOGGING" = true ] && echo "  ✓ Agent logging system"
[ "$UNINSTALL_VOICE" = true ] && echo "  ✓ Voice notifications"
echo ""

# Check if Claude settings exist
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
if [ ! -f "$CLAUDE_SETTINGS" ]; then
    echo -e "${YELLOW}No Claude settings file found. Nothing to uninstall.${NC}"
    exit 0
fi

# Create a Python script to remove our hooks
cat > /tmp/uninstall_claude_hooks.py << EOF
#!/usr/bin/env python3
import json
import sys

settings_file = "$CLAUDE_SETTINGS"
project_dir = "$PROJECT_DIR"
uninstall_logging = "$UNINSTALL_LOGGING" == "true"
uninstall_voice = "$UNINSTALL_VOICE" == "true"

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

# Commands to remove based on what's being uninstalled
our_hook_patterns = []

if uninstall_logging:
    our_hook_patterns.extend([
        f"python3 {project_dir}/hooks/log_session.py",
        f"python3 {project_dir}/hooks/log_agent_invocation.py"
    ])

if uninstall_voice:
    our_hook_patterns.extend([
        f"python3 {project_dir}/hooks/voice_notifier.py"
    ])

hooks_removed = []

# Process each hook event
for event in list(settings['hooks'].keys()):
    if event not in settings['hooks']:
        continue
    
    # Filter out our hooks
    filtered_config = []
    for item in settings['hooks'][event]:
        # Check if this item contains our hooks
        if 'hooks' in item:
            # Filter hooks within this item
            filtered_hooks = []
            for hook in item['hooks']:
                if 'command' in hook:
                    # Check if this is one of our commands
                    is_ours = any(pattern in hook['command'] for pattern in our_hook_patterns)
                    if is_ours:
                        hook_type = "logging" if "log_" in hook['command'] else "voice"
                        hooks_removed.append(f"{event} ({hook_type})")
                    else:
                        filtered_hooks.append(hook)
                else:
                    filtered_hooks.append(hook)
            
            # Update the item with filtered hooks
            if filtered_hooks:
                item['hooks'] = filtered_hooks
                filtered_config.append(item)
        else:
            filtered_config.append(item)
    
    # Update or remove the event
    if filtered_config:
        settings['hooks'][event] = filtered_config
    else:
        # Remove the event entirely if no hooks left
        del settings['hooks'][event]

# Clean up empty hooks section
if 'hooks' in settings and not settings['hooks']:
    del settings['hooks']

# Write updated settings
try:
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    
    if hooks_removed:
        print(f"✅ Removed hooks: {', '.join(set(hooks_removed))}")
    else:
        print("No matching hooks found for this project")
except Exception as e:
    print(f"❌ Error writing settings: {e}")
    sys.exit(1)
EOF

# Run the Python script to remove hooks
echo -e "${GREEN}Removing hooks from Claude settings...${NC}"
python3 /tmp/uninstall_claude_hooks.py

# Clean up
rm /tmp/uninstall_claude_hooks.py

# Check for global symlinks (only if uninstalling logging)
if [ "$UNINSTALL_LOGGING" = true ]; then
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
fi

# Summary
echo ""
echo -e "${GREEN}✅ Uninstall complete!${NC}"
echo ""

if [ "$UNINSTALL_LOGGING" = true ]; then
    echo "📊 Logging system removed:"
    echo "  • Agent invocation logging hooks"
    echo "  • Session tracking hooks"
    if [ "$REMOVED_SYMLINKS" = true ]; then
        echo "  • Global tool symlinks from /usr/local/bin"
    fi
    echo ""
fi

if [ "$UNINSTALL_VOICE" = true ]; then
    echo "🔊 Voice notifications removed:"
    echo "  • Stop event voice alerts"
    echo "  • Notification event voice alerts"
    echo ""
fi

echo "Note: The following remain (you can delete manually if desired):"
if [ "$UNINSTALL_LOGGING" = true ]; then
    echo "  • Log files in: $PROJECT_DIR/logs/"
    echo "  • Analysis tools in: $PROJECT_DIR/tools/"
fi
echo "  • Hook scripts in: $PROJECT_DIR/hooks/"
echo ""
echo -e "${YELLOW}⚠️  Restart Claude Code for changes to take effect${NC}"