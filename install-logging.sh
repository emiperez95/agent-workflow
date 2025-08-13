#!/bin/bash

# Install Agent Workflow Logging System
# This script configures Claude Code hooks for logging and notifications

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
INSTALL_LOGGING=false
INSTALL_VOICE=false
INSTALL_ALL=false

show_help() {
    echo ""
    echo -e "${BLUE}Agent Workflow Hook Installer${NC}"
    echo "==============================="
    echo ""
    echo "This script configures Claude Code hooks for this project."
    echo ""
    echo -e "${GREEN}Usage:${NC}"
    echo "  ./install-logging.sh [OPTIONS]"
    echo ""
    echo -e "${GREEN}Options:${NC}"
    echo "  -l, --logging     Install agent logging hooks"
    echo "                    Logs all agent invocations, execution times, and token usage"
    echo ""
    echo "  -v, --voice       Install voice notification hooks"
    echo "                    Speaks when Claude stops or needs attention"
    echo ""
    echo "  -a, --all         Install all available hooks"
    echo ""
    echo "  -h, --help        Show this help message"
    echo ""
    echo -e "${GREEN}Examples:${NC}"
    echo "  ./install-logging.sh --logging      # Install only logging"
    echo "  ./install-logging.sh --voice        # Install only voice notifications"
    echo "  ./install-logging.sh --all          # Install everything"
    echo "  ./install-logging.sh -l -v          # Install both logging and voice"
    echo ""
    echo -e "${YELLOW}Note:${NC} You'll need to restart Claude Code after installation"
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
            INSTALL_LOGGING=true
            shift
            ;;
        -v|--voice)
            INSTALL_VOICE=true
            shift
            ;;
        -a|--all)
            INSTALL_ALL=true
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
if [ "$INSTALL_ALL" = true ]; then
    INSTALL_LOGGING=true
    INSTALL_VOICE=true
fi

# Check if at least one feature is selected
if [ "$INSTALL_LOGGING" = false ] && [ "$INSTALL_VOICE" = false ]; then
    echo -e "${RED}Error: No features selected for installation${NC}"
    show_help
    exit 1
fi

echo ""
echo "🚀 Installing Agent Workflow Hooks"
echo "=================================="
echo "Project directory: $PROJECT_DIR"
echo ""

# Display what will be installed
echo -e "${GREEN}Features to install:${NC}"
[ "$INSTALL_LOGGING" = true ] && echo "  ✓ Agent logging system"
[ "$INSTALL_VOICE" = true ] && echo "  ✓ Voice notifications"
echo ""

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
install_logging = "$INSTALL_LOGGING" == "true"
install_voice = "$INSTALL_VOICE" == "true"

# Read existing settings
with open(settings_file, 'r') as f:
    settings = json.load(f)

# Ensure hooks section exists
if 'hooks' not in settings:
    settings['hooks'] = {}

# Define hook configurations
hook_config = {}

# Add logging hooks if requested
if install_logging:
    hook_config.update({
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
        ]
    })
    
    # Add Stop hook for logging
    if "Stop" not in hook_config:
        hook_config["Stop"] = [{"hooks": []}]
    hook_config["Stop"][0]["hooks"].append({
        "type": "command",
        "command": f"python3 {project_dir}/hooks/log_session.py --stop"
    })

# Add voice hooks if requested
if install_voice:
    # Add Stop hook for voice
    if "Stop" not in hook_config:
        hook_config["Stop"] = [{"hooks": []}]
    hook_config["Stop"][0]["hooks"].append({
        "type": "command",
        "command": f"python3 {project_dir}/hooks/voice_notifier.py stop"
    })
    
    # Add Notification hook for voice
    hook_config["Notification"] = [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": f"python3 {project_dir}/hooks/voice_notifier.py notification"
                }
            ]
        }
    ]

# Merge hook configuration
installed_features = []
for event, config in hook_config.items():
    if event not in settings['hooks']:
        settings['hooks'][event] = config
        installed_features.append(event)
    else:
        # Check if our hooks are already installed
        existing_commands = []
        for item in settings['hooks'][event]:
            if 'hooks' in item:
                for hook in item['hooks']:
                    if 'command' in hook:
                        existing_commands.append(hook['command'])
        
        # Add our hooks if not already present
        for hook_item in config:
            for hook in hook_item.get('hooks', []):
                if 'command' in hook and hook['command'] not in existing_commands:
                    # Find or create the appropriate entry
                    found = False
                    for existing_item in settings['hooks'][event]:
                        if 'matcher' in hook_item and 'matcher' in existing_item:
                            if hook_item['matcher'] == existing_item['matcher']:
                                existing_item['hooks'].append(hook)
                                found = True
                                break
                        elif 'matcher' not in hook_item and 'matcher' not in existing_item:
                            existing_item['hooks'].append(hook)
                            found = True
                            break
                    
                    if not found:
                        settings['hooks'][event].append(hook_item)
                    
                    installed_features.append(f"{event} ({hook['command'].split('/')[-1]})")

# Write updated settings
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

if installed_features:
    print(f"✅ Installed hooks for: {', '.join(set(installed_features))}")
else:
    print("✅ All requested hooks were already installed")
EOF

# Run the Python script to update settings
echo -e "${GREEN}Updating Claude settings...${NC}"
python3 /tmp/update_claude_settings.py

# Clean up
rm /tmp/update_claude_settings.py

# Create logs directory if logging is being installed
if [ "$INSTALL_LOGGING" = true ] && [ ! -d "$PROJECT_DIR/logs" ]; then
    echo -e "${GREEN}Creating logs directory...${NC}"
    mkdir -p "$PROJECT_DIR/logs/sessions"
fi

# Test voice if installed
if [ "$INSTALL_VOICE" = true ]; then
    echo ""
    read -p "Would you like to test voice notifications? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo '{"session_id": "test", "cwd": "/tmp"}' | python3 "$PROJECT_DIR/hooks/voice_notifier.py" stop
    fi
fi

# Success message
echo ""
echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""

if [ "$INSTALL_LOGGING" = true ]; then
    echo "📊 Logging system installed:"
    echo "  • Logs all agent invocations to $PROJECT_DIR/logs/"
    echo "  • Tracks execution times and token usage"
    echo "  • Captures agent prompts and responses"
    echo ""
    echo "  View logs with:"
    echo "    python3 $PROJECT_DIR/tools/monitor.py"
    echo "    python3 $PROJECT_DIR/tools/analyze_workflow.py"
    echo "    python3 $PROJECT_DIR/tools/tail_logs.py -f"
    echo ""
fi

if [ "$INSTALL_VOICE" = true ]; then
    echo "🔊 Voice notifications installed:"
    echo "  • Speaks when Claude stops working"
    echo "  • Alerts when Claude needs your attention"
    echo ""
fi

echo -e "${YELLOW}⚠️  Note: Restart Claude Code for hooks to take effect${NC}"
echo ""

# Optional: Add tools to PATH (only if logging was installed)
if [ "$INSTALL_LOGGING" = true ]; then
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
fi