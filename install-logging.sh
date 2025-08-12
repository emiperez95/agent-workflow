#!/bin/bash

# Install Agent Workflow Logging System
# This script configures Claude Code to log agent invocations for this project

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🚀 Installing Agent Workflow Logging System"
echo "=========================================="

# Get the absolute path to this project
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Project directory: $PROJECT_DIR"

# Check if Claude settings exist
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
if [ ! -f "$CLAUDE_SETTINGS" ]; then
    echo -e "${YELLOW}Creating new Claude settings file...${NC}"
    mkdir -p "$HOME/.claude"
    echo '{"hooks": {}}' > "$CLAUDE_SETTINGS"
fi

# Create a Python script to update the settings
cat > /tmp/update_claude_settings.py << EOF
#!/usr/bin/env python3
import json
import sys

settings_file = "$CLAUDE_SETTINGS"
project_dir = "$PROJECT_DIR"

# Read existing settings
with open(settings_file, 'r') as f:
    settings = json.load(f)

# Ensure hooks section exists
if 'hooks' not in settings:
    settings['hooks'] = {}

# Define our hook configuration
hook_config = {
    "SessionStart": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": f"python3 {project_dir}/hooks/log_session.py --start"
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
                    "command": f"python3 {project_dir}/hooks/log_agent_invocation.py"
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
                    "command": f"python3 {project_dir}/hooks/log_agent_invocation.py --post"
                }
            ]
        }
    ],
    "SubagentStop": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": f"python3 {project_dir}/hooks/log_agent_invocation.py --subagent-stop"
                }
            ]
        }
    ],
    "Stop": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": f"python3 {project_dir}/hooks/log_session.py --stop"
                }
            ]
        }
    ]
}

# Merge hook configuration
for event, config in hook_config.items():
    if event not in settings['hooks']:
        settings['hooks'][event] = config
    else:
        # Check if our hooks are already installed
        existing_commands = []
        for item in settings['hooks'][event]:
            if 'hooks' in item:
                for hook in item['hooks']:
                    if 'command' in hook:
                        existing_commands.append(hook['command'])
        
        # Add our config if not already present
        our_command = config[0]['hooks'][0]['command']
        if our_command not in existing_commands:
            settings['hooks'][event].extend(config)
            print(f"Added {event} hook")
        else:
            print(f"{event} hook already installed")

# Write updated settings
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print("✅ Settings updated successfully")
EOF

# Run the Python script to update settings
echo -e "${GREEN}Updating Claude settings...${NC}"
python3 /tmp/update_claude_settings.py

# Clean up
rm /tmp/update_claude_settings.py

# Create logs directory if it doesn't exist
if [ ! -d "$PROJECT_DIR/logs" ]; then
    echo -e "${GREEN}Creating logs directory...${NC}"
    mkdir -p "$PROJECT_DIR/logs/sessions"
fi

# Check if tools should be added to PATH
echo ""
echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo "The logging system is now active. It will:"
echo "  • Log all agent invocations to $PROJECT_DIR/logs/"
echo "  • Track execution times and token usage"
echo "  • Capture agent prompts and responses"
echo ""
echo "📊 To view logs, use:"
echo "  python3 $PROJECT_DIR/tools/monitor.py        # Check status"
echo "  python3 $PROJECT_DIR/tools/analyze_workflow.py  # Analyze patterns"
echo "  python3 $PROJECT_DIR/tools/tail_logs.py -f      # Live monitoring"
echo ""
echo -e "${YELLOW}⚠️  Note: Restart Claude Code for hooks to take effect${NC}"
echo ""

# Optional: Add tools to PATH
read -p "Would you like to add analysis tools to your PATH? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    TOOLS_DIR="$PROJECT_DIR/tools"
    
    # Create symlinks in /usr/local/bin
    echo -e "${GREEN}Creating symlinks...${NC}"
    
    for tool in analyze_workflow monitor query_logs tail_logs visualize_flow; do
        if [ -f "$TOOLS_DIR/${tool}.py" ]; then
            sudo ln -sf "$TOOLS_DIR/${tool}.py" "/usr/local/bin/agent-${tool}"
            echo "  Created: agent-${tool}"
        fi
    done
    
    echo -e "${GREEN}Tools available globally with 'agent-' prefix${NC}"
    echo "  Example: agent-monitor"
fi