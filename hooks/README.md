# Agent Workflow Logging Hooks

These Python scripts are Claude Code hooks that log agent invocations to track workflow patterns and performance.

## Files

- **`log_agent_invocation.py`** - Logs Task tool calls (agent invocations)
- **`log_session.py`** - Tracks session start/stop events

## How It Works

1. Claude Code triggers hooks on specific events (PreToolUse, PostToolUse, etc.)
2. Hook scripts receive event data via stdin as JSON
3. Data is stored in:
   - SQLite database: `logs/agent_workflow.db`
   - JSON files: `logs/sessions/[session_id].json`

## Installation

```bash
# From project root
./install-logging.sh
```

This will:
1. Add hook configuration to `~/.claude/settings.json`
2. Configure hooks to call these scripts with absolute paths
3. Create the `logs/` directory for data storage

## Data Captured

- Agent names and types
- Execution phases (requirements, planning, development, review, finalization)
- Full prompts sent to agents
- Execution times and token usage
- Success/failure status
- Parallel execution patterns

## Manual Configuration

If you prefer to configure manually, add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Task",
      "hooks": [{
        "type": "command",
        "command": "python3 /path/to/agent-workflow/hooks/log_agent_invocation.py"
      }]
    }],
    // ... other hooks
  }
}
```

## Requirements

- Python 3.6+
- No external dependencies (uses standard library only)

## Storage Location

Logs are stored in the project directory:
- `logs/agent_workflow.db` - SQLite database
- `logs/sessions/*.json` - Individual session files

This keeps logs project-local and doesn't pollute the global Claude configuration.