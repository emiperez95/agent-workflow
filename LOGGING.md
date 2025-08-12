# 📊 Agent Workflow Logging System

## Overview

This logging system tracks all agent invocations in the Claude Development Pipeline, providing complete observability into the development workflow. It captures agent calls, their context, execution times, and results to enable process optimization and agent discovery.

## 🚀 Quick Start

### Installation

```bash
# Run the installation script
./install-logging.sh

# This will:
# 1. Configure hooks in ~/.claude/settings.json
# 2. Create logs directory
# 3. Optionally add tools to PATH
```

**Note**: Restart Claude Code after installation for hooks to take effect.

### View Logs

```bash
# List recent sessions
python3 tools/query_logs.py sessions

# Show agents used in a specific session
python3 tools/query_logs.py show <session_id>

# Analyze workflow patterns
python3 tools/analyze_workflow.py

# Generate visualizations
python3 tools/visualize_flow.py --session <session_id> --type flow
```

## 📁 Architecture

### Directory Structure

```
agent-workflow/
├── hooks/                 # Hook scripts (stay in project)
│   ├── log_agent_invocation.py  # Main agent logging
│   └── log_session.py           # Session tracking
├── logs/                  # Log storage (project-local)
│   ├── agent_workflow.db  # SQLite database
│   └── sessions/          # JSON session files
│       └── [session_id].json
├── tools/                 # Analysis tools
│   ├── analyze_workflow.py    # Statistical analysis
│   ├── visualize_flow.py      # Flow diagrams
│   ├── query_logs.py          # Data exploration
│   ├── monitor.py             # Status checker
│   ├── tail_logs.py           # Live monitoring
│   └── watch.sh               # Quick live view
└── install-logging.sh     # Installation script

~/.claude/
└── settings.json          # Hook configuration (updated by installer)
```

### Data Flow

1. **Hook Trigger**: Claude Code triggers hooks on PreToolUse/PostToolUse events
2. **Data Capture**: Python scripts receive JSON via stdin
3. **Storage**: Data saved to SQLite database and JSON files
4. **Analysis**: Tools query database to generate insights

## 🎣 Hooks Configuration

### Captured Events

- **SessionStart**: New session begins
- **PreToolUse**: Before Task tool execution (agent start)
- **PostToolUse**: After Task tool completion (agent end)
- **SubagentStop**: Subagent finishes
- **Stop**: Session ends

### Hook Data Structure

```json
{
  "session_id": "abc123",
  "tool_name": "Task",
  "tool_input": {
    "subagent_type": "jira-analyst",
    "prompt": "Extract requirements from PROJ-123..."
  },
  "tool_response": {
    "result": "..."
  }
}
```

## 📊 Database Schema

### Tables

#### sessions
- `session_id` (PRIMARY KEY)
- `start_time`
- `end_time`
- `status`
- `cwd`
- `metadata`

#### agent_invocations
- `id` (AUTO INCREMENT)
- `timestamp`
- `session_id`
- `event_type`
- `phase` (requirements/planning/development/review/finalization)
- `agent_name`
- `agent_type`
- `model`
- `prompt`
- `parent_agent`
- `ticket_id`
- `start_time`
- `end_time`
- `duration_seconds`
- `status`
- `error`
- `result_summary`
- `raw_input`
- `raw_output`

## 🛠️ Analysis Tools

### 1. analyze_workflow.py

Generate comprehensive statistics:

```bash
# Full analysis report
python3 tools/analyze_workflow.py

# Analyze specific session
python3 tools/analyze_workflow.py --session <session_id>

# Export session data
python3 tools/analyze_workflow.py --export <session_id>
```

**Reports include:**
- Agent usage frequency
- Average execution times
- Phase distribution
- Common agent sequences
- Parallel execution patterns
- Performance bottlenecks

### 2. visualize_flow.py

Create visual representations:

```bash
# Flow diagram
python3 tools/visualize_flow.py --session <session_id> --type flow

# Gantt chart (timeline)
python3 tools/visualize_flow.py --session <session_id> --type gantt

# Network graph (agent relationships)
python3 tools/visualize_flow.py --session <session_id> --type network

# All visualizations
python3 tools/visualize_flow.py --session <session_id> --type all --output my_session
```

**Output formats:**
- Mermaid diagrams (paste into GitHub, mermaid.live, or any Mermaid-compatible viewer)
- Saved to `visualizations/` directory

### 3. query_logs.py

Interactive log exploration:

```bash
# List sessions
python3 tools/query_logs.py sessions --limit 20

# Show session details
python3 tools/query_logs.py show <session_id>

# Find patterns
python3 tools/query_logs.py patterns --min 5

# View agent prompts
python3 tools/query_logs.py prompts jira-analyst --limit 10

# Search logs
python3 tools/query_logs.py search "PROJ-123" --field prompt

# Export data
python3 tools/query_logs.py export --session <session_id> --format json
python3 tools/query_logs.py export --format csv
```

## 📈 Use Cases

### 1. Process Optimization

Identify slow agents and bottlenecks:

```bash
python3 tools/analyze_workflow.py | grep BOTTLENECK -A 5
```

### 2. Agent Discovery

Find gaps where new agents could help:

```bash
# Look for common sequences that could be combined
python3 tools/query_logs.py patterns --min 10
```

### 3. Debugging Workflows

Trace issues through the agent chain:

```bash
# Search for errors
python3 tools/query_logs.py search "error" --field error

# View specific session flow
python3 tools/visualize_flow.py --session <session_id> --type flow
```

### 4. Performance Monitoring

Track execution times over time:

```bash
# Export data for external analysis
python3 tools/query_logs.py export --format csv

# Analyze in Excel, Jupyter, or other tools
```

## 🔍 Example Queries

### Find Most Used Agents

```sql
SELECT agent_name, COUNT(*) as count
FROM agent_invocations
WHERE agent_name != 'unknown'
GROUP BY agent_name
ORDER BY count DESC;
```

### Parallel Execution Analysis

```sql
SELECT a1.agent_name, a2.agent_name, COUNT(*) as parallel_count
FROM agent_invocations a1
JOIN agent_invocations a2 ON a1.session_id = a2.session_id
WHERE a1.start_time <= a2.end_time
  AND a1.end_time >= a2.start_time
  AND a1.id != a2.id
GROUP BY a1.agent_name, a2.agent_name;
```

### Session Performance

```sql
SELECT 
  session_id,
  COUNT(*) as agent_count,
  SUM(duration_seconds) as total_duration,
  AVG(duration_seconds) as avg_duration
FROM agent_invocations
GROUP BY session_id
ORDER BY total_duration DESC;
```

## 🚧 Troubleshooting

### No Logs Appearing

1. Check hooks are enabled:
   ```bash
   cat .claude/settings.json
   ```

2. Verify Python 3 is installed:
   ```bash
   python3 --version
   ```

3. Check hook script permissions:
   ```bash
   ls -la .claude/hooks/*.py
   ```

4. Look for errors in Claude Code output (hooks print to stderr)

### Database Errors

Reset the database:
```bash
rm .claude/logs/agent_workflow.db
# Logs will recreate database on next run
```

### Missing Dependencies

Install required Python packages:
```bash
pip3 install tabulate
```

## 🔮 Future Enhancements

- **Real-time Dashboard**: Web interface for live monitoring
- **Webhooks**: Send events to external monitoring systems
- **ML Analysis**: Automatic pattern detection and optimization suggestions
- **Cost Tracking**: Monitor token usage per agent
- **Alert System**: Notify on failures or performance degradation
- **Agent Recommendations**: Suggest new agents based on usage patterns

## 🤝 Contributing

To improve the logging system:

1. **Add New Metrics**: Extend database schema and capture additional data
2. **Create Visualizations**: Add new chart types or improve existing ones
3. **Enhance Analysis**: Develop new pattern detection algorithms
4. **Share Insights**: Document interesting patterns you discover

## 📝 Notes

- Logs are stored locally in `.claude/logs/` (add to .gitignore if needed)
- Session JSON files provide backup and easy sharing
- SQLite database enables complex queries and analysis
- All timestamps are in ISO format for consistency
- The system has minimal performance impact on agent execution