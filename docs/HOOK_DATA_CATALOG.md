# Hook Data Catalog

## Overview
This document catalogs all data captured by the Claude Code logging hooks system. It details what information each hook collects, how it's stored, and how to extract insights from the captured data.

## Database Schema

### Tables Structure
- **sessions**: 6 fields tracking session lifecycle
- **agent_invocations**: 19 fields tracking agent execution
- **agent_tool_uses**: 14 fields tracking tool usage within agents
- **tool_uses**: 7 fields for basic tool tracking

## Hook-by-Hook Data Collection

### 1. Session Logger (`log_session.py`)

#### Triggered Events
- `SessionStart`: When a Claude session begins
- `Stop`: When a session ends

#### Data Captured

##### Database Fields (sessions table)
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| session_id | TEXT | Unique session identifier | `2ff9e2d5-b271-44a4-bb03-d9c93b066b9f` |
| start_time | TIMESTAMP | Session start timestamp | `2025-08-16T16:55:26.401799` |
| end_time | TIMESTAMP | Session end timestamp | `2025-08-16T17:23:45.123456` |
| status | TEXT | Session status | `active`, `completed` |
| cwd | TEXT | Working directory | `/Users/emilianoperez/Projects/00-Personal/agent-workflow` |
| metadata | JSON | Full hook data | Contains transcript_path, source, etc. |

##### JSON File Storage
- Location: `logs/sessions/{session_id}.json`
- Contains chronological event stream
- Includes session_start and session_stop events

#### Extractable Metrics
- Session duration
- Sessions per day/hour
- Working directory patterns
- Session completion rate

### 2. Agent Invocation Logger (`log_agent_invocation.py`)

#### Triggered Events
- `PreToolUse` (Task tool only): Agent starts
- `PostToolUse` (Task tool only): Agent completes
- `SubagentStop`: Subagent termination

#### Data Captured

##### Database Fields (agent_invocations table)
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | INTEGER | Auto-increment ID | `1` |
| timestamp | TIMESTAMP | Event timestamp | `2025-08-16T10:30:15.123456` |
| session_id | TEXT | Parent session ID | `2ff9e2d5-b271-44a4-bb03-d9c93b066b9f` |
| event_type | TEXT | Event classification | `pre_invocation`, `subagent_stop` |
| phase | TEXT | Workflow phase | `requirements`, `planning`, `development`, `review`, `finalization` |
| agent_name | TEXT | Agent identifier | `context-analyzer`, `backend-developer` |
| agent_type | TEXT | Agent category | Same as phase |
| model | TEXT | AI model used | Currently unpopulated |
| prompt | TEXT | Agent prompt | Full task description |
| parent_agent | TEXT | Calling agent | Currently unpopulated |
| ticket_id | TEXT | Extracted ticket | `PROJ-123` |
| start_time | TIMESTAMP | Execution start | `2025-08-16T10:30:15.123456` |
| end_time | TIMESTAMP | Execution end | `2025-08-16T10:31:45.789012` |
| duration_seconds | REAL | Execution time | `90.5` |
| status | TEXT | Completion status | `started`, `completed` |
| error | TEXT | Error message | Error details if failed |
| result_summary | TEXT | Result synopsis | Currently unpopulated |
| raw_input | JSON | Complete input | Full Task tool input |
| raw_output | JSON | Complete output | Full Task tool response |

##### Agent Classification Logic
```python
# Phase determination based on agent name
requirements: jira-analyst, context-analyzer, requirements-clarifier
planning: agent-discoverer, story-analyzer, architect, task-planner
development: backend-developer, frontend-developer, database-developer, test-developer
review: performance-reviewer, security-reviewer, maintainability-reviewer, test-validator
finalization: documentation-generator, changelog-writer, pr-creator
```

#### Extractable Metrics
- Agent usage frequency (top agents: context-analyzer: 28, backend-developer: 11)
- Phase distribution and duration
- Success/failure rates by agent
- Prompt complexity analysis
- Error patterns by agent type
- Workflow sequences

### 3. Tool Operations Logger (`log_tool_operations.py`)

#### Triggered Events
- `PreToolUse` (all tools): Tool execution starts
- `PostToolUse` (all tools): Tool execution completes

#### Data Captured

##### Database Fields (agent_tool_uses table)
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | INTEGER | Auto-increment ID | `1` |
| timestamp | TIMESTAMP | Event timestamp | `2025-08-16T10:30:20.123456` |
| session_id | TEXT | Parent session ID | `2ff9e2d5-b271-44a4-bb03-d9c93b066b9f` |
| agent_name | TEXT | Current agent context | `backend-developer`, `direct` |
| agent_invocation_id | INTEGER | Agent instance ID | `1` |
| tool_name | TEXT | Tool identifier | `Read`, `Edit`, `Bash` |
| tool_input | JSON | Tool parameters | Complete tool input |
| tool_output | JSON | Tool response | Complete tool output |
| duration_seconds | REAL | Execution time | `0.125` |
| status | TEXT | Completion status | `started`, `completed`, `error` |
| error | TEXT | Error details | Error message if failed |
| sequence_number | INTEGER | Tool order in agent | `1`, `2`, `3`... |
| start_time | TIMESTAMP | Tool start time | `2025-08-16T10:30:20.123456` |
| end_time | TIMESTAMP | Tool end time | `2025-08-16T10:30:20.248456` |

##### Special Behaviors
- **Task tool**: Creates new agent context
- **Other tools**: Execute within current agent context
- **No agent context**: Uses "direct" as agent_name

##### Context Tracking
- File: `logs/current_agent_context.json`
- Maintains active agent and sequence number
- Cleared when Task tool completes

#### Extractable Metrics
- Tool usage frequency per agent
- Tool execution times
- Tool failure rates
- Tool sequences within agents
- Most resource-intensive tools

### 4. Voice Notifier (`voice_notifier.py`)

#### Triggered Events
- `Stop`: Session end notification
- `Notification`: General notifications

#### Data Captured
- No database storage
- Audio notifications only
- Terminal output for debugging

## Current Data Statistics

### Volume (as of latest check)
- **Sessions**: 29 total
- **Agent Invocations**: 212 total
- **Agent Tool Uses**: 1 record (underutilized)
- **Tool Uses**: 0 records (unused table)

### Coverage
- **Unique Sessions**: 18
- **Unique Agents**: 18 types tracked
- **Workflow Phases**: 6 (including 'unknown')
- **Most Used Agents**:
  1. Unknown/unclassified: 103
  2. context-analyzer: 28
  3. backend-developer: 11
  4. architect: 10

## SQL Query Examples

### Session Analytics
```sql
-- Average session duration
SELECT 
    AVG(julianday(end_time) - julianday(start_time)) * 24 * 60 as avg_duration_minutes
FROM sessions 
WHERE end_time IS NOT NULL;

-- Sessions by day
SELECT 
    DATE(start_time) as day,
    COUNT(*) as session_count
FROM sessions
GROUP BY DATE(start_time)
ORDER BY day DESC;
```

### Agent Performance
```sql
-- Agent success rates
SELECT 
    agent_name,
    COUNT(*) as total_invocations,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
    ROUND(100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM agent_invocations
WHERE agent_name != ''
GROUP BY agent_name
ORDER BY total_invocations DESC;

-- Phase distribution
SELECT 
    phase,
    COUNT(*) as invocation_count,
    COUNT(DISTINCT session_id) as unique_sessions
FROM agent_invocations
WHERE phase IS NOT NULL
GROUP BY phase
ORDER BY invocation_count DESC;
```

### Tool Usage Patterns
```sql
-- Tool usage by agent (when data is available)
SELECT 
    agent_name,
    tool_name,
    COUNT(*) as usage_count,
    AVG(duration_seconds) as avg_duration
FROM agent_tool_uses
GROUP BY agent_name, tool_name
ORDER BY usage_count DESC;

-- Tool sequence analysis
SELECT 
    agent_name,
    GROUP_CONCAT(tool_name ORDER BY sequence_number) as tool_sequence
FROM agent_tool_uses
GROUP BY agent_name, agent_invocation_id;
```

### Error Analysis
```sql
-- Error frequency by agent
SELECT 
    agent_name,
    COUNT(*) as error_count,
    error
FROM agent_invocations
WHERE error IS NOT NULL
GROUP BY agent_name, error
ORDER BY error_count DESC;

-- Failed tool operations
SELECT 
    tool_name,
    COUNT(*) as failure_count,
    error
FROM agent_tool_uses
WHERE status = 'error'
GROUP BY tool_name, error;
```

## Data Quality Issues

### Current Problems
1. **Incomplete Duration Tracking**: Most duration_seconds fields are NULL
2. **Underutilized Tables**: agent_tool_uses has minimal data
3. **Missing Classifications**: 103 invocations with no agent_name
4. **Unpopulated Fields**: model, parent_agent, result_summary rarely used

### Recommended Fixes
1. Calculate duration from start_time/end_time timestamps
2. Ensure tool operations hook properly captures all tool uses
3. Improve agent name extraction logic
4. Populate model field from agent configuration

## Data Export Formats

### Prometheus Metrics
The `prometheus_exporter.py` exposes metrics at `http://localhost:9090/metrics`:
- `agent_invocations_total`: Counter by agent/phase/status
- `agent_duration_seconds`: Histogram by agent/phase
- `session_duration_seconds`: Histogram
- `database_info`: Gauge with database statistics

### JSON Session Files
Complete session history in `logs/sessions/{session_id}.json`:
- Chronological event stream
- Full agent invocation details
- Suitable for replay/debugging

## Privacy & Security Considerations

### Sensitive Data Captured
- Full file paths in working directory
- Complete prompts which may contain proprietary information
- Session IDs that could be correlated
- Tool inputs/outputs with potential secrets

### Recommendations
1. Hash session IDs for anonymization
2. Redact sensitive paths in exports
3. Filter prompts for secrets before storage
4. Implement data retention policies
5. Secure database file permissions

## Enhanced Data Capture (NEW)

### Transcript Parser Tool
The `tools/parse_transcript.py` utility extracts rich data from Claude transcript files:

#### Additional Tables Created
- **transcript_events**: 22 fields including UUIDs, thinking, usage stats
- **thinking_logs**: Claude's internal reasoning process
- **tool_relationships**: Parent-child UUID relationships

#### Key Metrics Now Available
- **Token Usage**: Total, input, output, cache read/create tokens
- **Performance**: Duration in milliseconds for each tool use
- **Relationships**: Full parent-child UUID tracking
- **Git Context**: Branch information for each event
- **Claude Version**: Version tracking per event
- **Thinking Process**: Claude's internal reasoning captured

### Example Session Analysis
Session `2ff9e2d5-b271-44a4-bb03-d9c93b066b9f`:
- **Total Tokens**: 39,938,482 (39.9M!)
- **Cache Efficiency**: 90.8% cache hits (36.3M cached vs 3.5M created)
- **Events**: 1,166 transcript events
- **Tool Uses**: 33 distinct tool invocations
- **Thinking Logs**: 36 reasoning segments
- **Relationships**: 1,154 parent-child connections

### Data Completeness Improvements

#### Hook Updates Applied
1. **log_session.py**: 
   - Added git branch extraction
   - Capture transcript_path consistently
   - Store stop_hook_active flag

2. **log_agent_invocation.py**:
   - Extract token usage from responses
   - Calculate duration from totalDurationMs
   - Populate model field from service_tier

3. **log_tool_operations.py**:
   - (Still needs enhancement for better tracking)

### Verification Tools
- `tools/verify_hook_data.py`: Compares hook data with transcripts
- `tools/parse_transcript.py`: Extracts full transcript data

## Future Enhancements

### Completed ✅
1. ✅ Create transcript parser for rich data extraction
2. ✅ Add token usage tracking
3. ✅ Capture git branch and version
4. ✅ Store parent/child relationships
5. ✅ Extract thinking process

### High Priority
1. Fix tool_uses table population (only 1 record vs 212 invocations)
2. Implement real-time transcript monitoring
3. Add cost calculation based on token usage
4. Create data reconciliation between hooks and transcripts

### Medium Priority
1. Add memory/CPU resource tracking
2. Build automated alerts for high token usage
3. Create visualization dashboards
4. Add workflow pattern detection

### Low Priority
1. Implement data archival strategy
2. Add export to various formats
3. Build anomaly detection system