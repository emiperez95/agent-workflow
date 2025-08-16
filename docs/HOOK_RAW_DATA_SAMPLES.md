# Hook Raw Data Samples

This document contains actual raw data captured by the Claude Code logging hooks, showing the exact format and content of data being stored in the database and JSON files.

## 1. Sessions Table Raw Data

### Recent Session Records (Complete)
```
session_id|start_time|end_time|status|cwd|metadata
2ff9e2d5-b271-44a4-bb03-d9c93b066b9f|2025-08-16T16:55:26.401799|2025-08-16T17:01:01.009584|completed|/Users/emilianoperez/Projects/00-Personal/agent-workflow|{"session_id": "2ff9e2d5-b271-44a4-bb03-d9c93b066b9f", "transcript_path": "/Users/emilianoperez/.claude/projects/-Users-emilianoperez-Projects-00-Personal-agent-workflow/2ff9e2d5-b271-44a4-bb03-d9c93b066b9f.jsonl", "cwd": "/Users/emilianoperez/Projects/00-Personal/agent-workflow", "hook_event_name": "SessionStart", "source": "compact"}

6f6b4a05-5d81-4e59-852f-f37e081c31df|2025-08-15T10:53:37.624655||active|/Users/emilianoperez/Projects/01-wyeworks/01-clear-session|{"session_id": "6f6b4a05-5d81-4e59-852f-f37e081c31df", "transcript_path": "/Users/emilianoperez/.claude/projects/-Users-emilianoperez-Projects-01-wyeworks-01-clear-session/6f6b4a05-5d81-4e59-852f-f37e081c31df.jsonl", "cwd": "/Users/emilianoperez/Projects/01-wyeworks/01-clear-session", "hook_event_name": "SessionStart", "source": "clear"}

adbfc5f9-df57-4456-b5f5-62e1f8b7216d|2025-08-15T10:34:15.659522|2025-08-15T10:53:45.537602|completed|/Users/emilianoperez/Projects/01-wyeworks/02-features/maintenance/pr-feedback-and-fixes|{"session_id": "adbfc5f9-df57-4456-b5f5-62e1f8b7216d", "transcript_path": "/Users/emilianoperez/.claude/projects/-Users-emilianoperez-Projects-01-wyeworks-02-features-maintenance-pr-feedback-and-fixes/adbfc5f9-df57-4456-b5f5-62e1f8b7216d.jsonl", "cwd": "/Users/emilianoperez/Projects/01-wyeworks/02-features/maintenance/pr-feedback-and-fixes", "hook_event_name": "SessionStart", "source": "clear"}
```

### Session JSON File Raw Content
`logs/sessions/2ff9e2d5-b271-44a4-bb03-d9c93b066b9f.json`:
```json
[
  {
    "timestamp": "2025-08-16T16:55:26.401799",
    "event": "session_start",
    "cwd": "/Users/emilianoperez/Projects/00-Personal/agent-workflow",
    "metadata": {
      "session_id": "2ff9e2d5-b271-44a4-bb03-d9c93b066b9f",
      "transcript_path": "/Users/emilianoperez/.claude/projects/-Users-emilianoperez-Projects-00-Personal-agent-workflow/2ff9e2d5-b271-44a4-bb03-d9c93b066b9f.jsonl",
      "cwd": "/Users/emilianoperez/Projects/00-Personal/agent-workflow",
      "hook_event_name": "SessionStart",
      "source": "compact"
    }
  },
  {
    "timestamp": "2025-08-16T17:01:01.009584",
    "event": "session_stop"
  }
]
```

## 2. Agent Invocations Table Raw Data

### Complete Agent Invocation Record (backend-developer)
```
id: 211
timestamp: 2025-08-15T12:29:58.736591
session_id: 9fd0a293-b2b2-4599-a6d6-72ed8a60af4e
event_type: pre_invocation
phase: development
agent_name: backend-developer
agent_type: development
model: 
prompt: There are 11 remaining test failures in the NLP service that need to be fixed. Based on the previous analysis, the main issues are:

1. **Date entity selection order**: Tests expect `symbol-1-id` but getting `symbol-2-id` - this is about entity selection order when accuracy/length are equal
2. **Malformed pattern results**: Tests expect results with empty source but may be getting null
3. **Mixed pattern text handling**: Wrong source/branch extraction in complex text  
4. **Special regex character handling**: Entity names with special characters not matching properly
5. **Integration test undefined returns**: `entityExtraction` returning undefined instead of expected objects

Key requirements:
- When accuracy and length are equal between entities, prefer the FIRST entity (lower index) for test consistency
- For malformed patterns, return results with empty source string, not null
- Handle special regex characters in entity names properly 
- Ensure `entityExtraction` never returns undefined when there are valid entities - should return objects with `branchingEntity: null` for 2+ entity cases that don't match patterns
- Fix mixed pattern validation to extract correct source and branches

Files to focus on:
- `/Users/emilianoperez/Projects/01-wyeworks/02-features/CSD-2308/apps/server/src/Nlp/nlp.service.ts`

The goal is to get all 146 tests passing. Focus on the entity selection logic, pattern validation, and ensuring consistent return types from `entityExtraction`.
parent_agent: 
ticket_id: 
start_time: 2025-08-15T12:29:58.736591
end_time: 2025-08-15T12:41:53.051236
duration_seconds: 
status: completed
error: 
result_summary: 
```

### Raw Input JSON (backend-developer)
```json
{
  "description": "Fix final NLP test failures",
  "prompt": "There are 11 remaining test failures in the NLP service that need to be fixed. Based on the previous analysis, the main issues are:\n\n1. **Date entity selection order**: Tests expect `symbol-1-id` but getting `symbol-2-id` - this is about entity selection order when accuracy/length are equal\n2. **Malformed pattern results**: Tests expect results with empty source but may be getting null\n3. **Mixed pattern text handling**: Wrong source/branch extraction in complex text  \n4. **Special regex character handling**: Entity names with special characters not matching properly\n5. **Integration test undefined returns**: `entityExtraction` returning undefined instead of expected objects\n\nKey requirements:\n- When accuracy and length are equal between entities, prefer the FIRST entity (lower index) for test consistency\n- For malformed patterns, return results with empty source string, not null\n- Handle special regex characters in entity names properly \n- Ensure `entityExtraction` never returns undefined when there are valid entities - should return objects with `branchingEntity: null` for 2+ entity cases that don't match patterns\n- Fix mixed pattern validation to extract correct source and branches\n\nFiles to focus on:\n- `/Users/emilianoperez/Projects/01-wyeworks/02-features/CSD-2308/apps/server/src/Nlp/nlp.service.ts`\n\nThe goal is to get all 146 tests passing. Focus on the entity selection logic, pattern validation, and ensuring consistent return types from `entityExtraction`.",
  "subagent_type": "backend-developer"
}
```

### Raw Output JSON (backend-developer)
```json
{
  "content": [
    {
      "type": "text",
      "text": "## Summary\n\nI've successfully fixed the NLP service issues in `/Users/emilianoperez/Projects/01-wyeworks/02-features/CSD-2308/apps/server/src/Nlp/nlp.service.ts`. Here's what I accomplished:\n\n### Fixed Issues:\n\n1. **✅ Entity Selection Order**: Fixed the entity sorting logic to prefer entities with higher accuracy first, then higher length, and finally the first entity (lower index) when accuracy and length are equal. This ensures consistent test results.\n\n2. **✅ Malformed Pattern Handling**: Added proper support for both 2-entity and 3-entity malformed patterns. When patterns like \"depending on,\" or \"based on,\" are malformed (missing condition after \"on\"), they return results with empty source strings as expected by tests.\n\n3. **✅ Special Regex Character Handling**: Implemented robust entity name matching that handles special characters like `+` properly by creating a helper method `entityAppearsInText()` that does safe text matching without regex interpretation issues.\n\n4. **✅ Mixed Pattern Validation**: Enhanced the validation logic with better entity-to-text alignment checking, allowing the service to correctly handle complex patterns with multiple entities.\n\n5. **✅ EntityExtraction Return Types**: Ensured that `entityExtraction` returns proper objects with `branchingEntity: null` for 2+ entity cases that don't match patterns, rather than returning undefined.\n\n### Test Results:\n- **Before**: 11 failing tests out of 146 total tests\n- **After**: 6 failing tests out of 146 total tests (5 tests fixed)\n\nThe remaining 6 failing tests are mostly related to:\n- Integration test mocking issues (3 tests returning undefined due to mock setup problems)  \n- Entity selection order in some edge cases (2 tests expecting symbol-1-id but getting symbol-2-id)\n- One complex mixed pattern case that requires more comprehensive changes\n\n### Key Files Modified:\n- `/Users/emilianoperez/Projects/01-wyeworks/02-features/CSD-2308/apps/server/src/Nlp/nlp.service.ts` - Enhanced pattern matching, entity selection, and validation logic\n\nThe NLP service is now significantly more robust and handles edge cases much better, bringing the test success rate from ~92% to ~96%."
    }
  ],
  "totalDurationMs": 714259,
  "totalTokens": 128692,
  "totalToolUseCount": 97,
  "usage": {
    "input_tokens": 0,
    "cache_creation_input_tokens": 5142,
    "cache_read_input_tokens": 123013,
    "cache_creation": {
      "ephemeral_5m_input_tokens": 5142,
      "ephemeral_1h_input_tokens": 0
    },
    "output_tokens": 537,
    "service_tier": "standard"
  }
}
```

### Complete Agent Invocation Record (requirements-clarifier)
```
id: 209
timestamp: 2025-08-15T10:51:13.901540
session_id: adbfc5f9-df57-4456-b5f5-62e1f8b7216d
event_type: pre_invocation
phase: requirements
agent_name: requirements-clarifier
agent_type: requirements
model: 
prompt: Based on PR 2545 with the following context:

**PR Purpose**: Removing URL state atoms and single component atoms as part of Recoil cleanup Phase 1

**Review Comments Found**:
1. Copilot suggests simplifying useSessionId hook to avoid unnecessary state/effects
2. Copilot found bug in DoctorOnboardingTool pathname check
3. Damimd10 requests:
   - Create a type for 'A' | 'B' version strings  
   - Rename generic 'Props' to 'SessionEditorProps'
   - Improve useSessionId to handle string[] query params properly

**Status**: Changes requested by Damimd10

Generate 3-4 targeted questions to clarify the implementation approach and ensure all feedback is addressed properly.
parent_agent: 
ticket_id: 
start_time: 2025-08-15T10:51:13.901540
end_time: 2025-08-15T10:53:29.241379
duration_seconds: 
status: completed
error: 
result_summary: 
```

## 3. Agent Tool Uses Table Raw Data

### Single Record (Limited Data Available)
```
id: 1
timestamp: 
session_id: 
agent_name: 
agent_invocation_id: 
tool_name: 
tool_input: {}
tool_output: 
duration_seconds: 
status: 
error: 
sequence_number: 
start_time: 
end_time: 
```

## 4. Database Summary Statistics

### Record Counts by Table
```sql
SELECT COUNT(*) as count, 'sessions' as table_name FROM sessions 
UNION ALL SELECT COUNT(*), 'agent_invocations' FROM agent_invocations 
UNION ALL SELECT COUNT(*), 'agent_tool_uses' FROM agent_tool_uses 
UNION ALL SELECT COUNT(*), 'tool_uses' FROM tool_uses;
```
Results:
```
29|sessions
212|agent_invocations
1|agent_tool_uses
0|tool_uses
```

### Agent Usage Distribution
```sql
SELECT DISTINCT agent_name, COUNT(*) as invocations 
FROM agent_invocations 
GROUP BY agent_name 
ORDER BY invocations DESC 
LIMIT 10;
```
Results:
```
|103
context-analyzer|28
backend-developer|11
architect|10
security-reviewer|7
performance-reviewer|7
test-developer|6
maintainability-reviewer|6
duplication-checker|6
requirements-clarifier|5
```

### Phase Distribution
```sql
SELECT DISTINCT phase FROM agent_invocations WHERE phase IS NOT NULL;
```
Results:
```
requirements
planning
unknown
development
review
finalization
```

### Session Summary Stats
```sql
SELECT 
    COUNT(DISTINCT session_id) as unique_sessions,
    COUNT(DISTINCT agent_name) as unique_agents,
    COUNT(DISTINCT phase) as unique_phases 
FROM agent_invocations;
```
Results:
```
18|18|6
```

## 5. Hook Event Raw Payloads

### SessionStart Hook Input (stdin to log_session.py)
```json
{
  "session_id": "2ff9e2d5-b271-44a4-bb03-d9c93b066b9f",
  "transcript_path": "/Users/emilianoperez/.claude/projects/-Users-emilianoperez-Projects-00-Personal-agent-workflow/2ff9e2d5-b271-44a4-bb03-d9c93b066b9f.jsonl",
  "cwd": "/Users/emilianoperez/Projects/00-Personal/agent-workflow",
  "hook_event_name": "SessionStart",
  "source": "compact"
}
```

### PreToolUse Hook Input for Task Tool (stdin to log_agent_invocation.py)
```json
{
  "session_id": "9fd0a293-b2b2-4599-a6d6-72ed8a60af4e",
  "tool_name": "Task",
  "tool_input": {
    "description": "Fix final NLP test failures",
    "prompt": "There are 11 remaining test failures in the NLP service that need to be fixed...",
    "subagent_type": "backend-developer"
  }
}
```

### PostToolUse Hook Input for Task Tool (stdin to log_agent_invocation.py)
```json
{
  "session_id": "9fd0a293-b2b2-4599-a6d6-72ed8a60af4e",
  "tool_name": "Task",
  "tool_input": {
    "description": "Fix final NLP test failures",
    "prompt": "...",
    "subagent_type": "backend-developer"
  },
  "tool_response": {
    "content": [
      {
        "type": "text",
        "text": "## Summary\n\nI've successfully fixed the NLP service issues..."
      }
    ],
    "totalDurationMs": 714259,
    "totalTokens": 128692,
    "totalToolUseCount": 97,
    "usage": {
      "input_tokens": 0,
      "cache_creation_input_tokens": 5142,
      "cache_read_input_tokens": 123013,
      "cache_creation": {
        "ephemeral_5m_input_tokens": 5142,
        "ephemeral_1h_input_tokens": 0
      },
      "output_tokens": 537,
      "service_tier": "standard"
    }
  }
}
```

### Stop Hook Input (stdin to log_session.py)
```json
{
  "session_id": "2ff9e2d5-b271-44a4-bb03-d9c93b066b9f",
  "hook_event_name": "Stop"
}
```

## 6. Context File Sample

### Current Agent Context (logs/current_agent_context.json)
```json
{
  "agent_name": "backend-developer",
  "agent_invocation_id": 1,
  "tool_sequence_number": 3
}
```

## 7. Empty/Unpopulated Fields

### Fields Commonly NULL or Empty:
- `model` - Never populated in agent_invocations
- `parent_agent` - Never populated
- `ticket_id` - Rarely extracted successfully
- `duration_seconds` - Calculation appears broken
- `result_summary` - Never populated
- `error` - Only populated on failures

### Underutilized Tables:
- `tool_uses` - 0 records (table exists but unused)
- `agent_tool_uses` - Only 1 record despite 212 agent invocations

## 8. Data Anomalies

### Unclassified Agents
- 103 invocations with empty agent_name (48.6% of all invocations)
- Indicates agent extraction logic issues

### Missing Durations
- Most records have NULL duration_seconds despite having start_time and end_time
- Calculation logic may be broken

### Tool Tracking Gap
- 212 agent invocations but only 1 tool use recorded
- Hook may not be properly capturing tool operations within agents

## 9. Enhanced Transcript Data (NEW)

### Transcript Events Table Sample
```sql
SELECT * FROM transcript_events WHERE session_id = '2ff9e2d5-b271-44a4-bb03-d9c93b066b9f' LIMIT 1;
```
```
id: 1
session_id: 2ff9e2d5-b271-44a4-bb03-d9c93b066b9f
uuid: 35edb0ad-f59d-4bb1-94de-0c4a85299578
parent_uuid: NULL
timestamp: 2025-08-14T12:14:24.258Z
event_type: system
tool_use_id: acd5508f-0739-4ebb-920b-8c21c58bdfa7
git_branch: master
claude_version: 1.0.77
user_type: external
is_meta: 0
is_sidechain: 0
content: SessionStart:clear [python3 /Users/emilianoperez/Projects/00-Personal/agent-workflow/hooks/log_session.py --start] completed successfully
message: NULL
usage: {}
thinking: NULL
duration_ms: NULL
tokens_total: 0
tokens_input: 0
tokens_output: 0
tokens_cache_read: 0
tokens_cache_create: 0
service_tier: NULL
```

### Thinking Logs Table Sample
```sql
SELECT * FROM thinking_logs WHERE session_id = '2ff9e2d5-b271-44a4-bb03-d9c93b066b9f' LIMIT 1;
```
```
id: 1
session_id: 2ff9e2d5-b271-44a4-bb03-d9c93b066b9f
event_uuid: cea993b0-c97b-4efd-9530-404b88617616
timestamp: 2025-08-14T12:15:34.821Z
thinking_content: The user is asking me to analyze the current state of the project, the files we have, and pending technical debt. They specifically said "Don't follow the base flow, just use the agents you think you need as parallel as possible."

This is interesting - they're using the dev-orchestrator command but asking me to deviate from its normal workflow. They want me to analyze the project state rather than implement a Jira ticket.

Given this request, I should:
1. Use the context-analyzer agent to understand the codebase structure and patterns
2. Use the duplication-checker agent to find code duplication issues
3. Use the maintainability-reviewer to assess code quality
4. Maybe use the architect agent to review architecture

Let me start by running multiple agents in parallel to gather information about the project.
signature: Et0HCkYIBhgCKkDjdNG5/4UT6zIoOYMD6NJnJ+U0cibZJucm5/U5Xx4sgusFPh7xfqB4Vxk2PoEO2HWxhNtq3+LEGP5AyoelKDTtEgwK2wcuclhDHqM3SPQaDAN9SN7YZ4MSnhp81SIwqpjmCF2JtfWZVd9fNJFTOUDZcKQI4XQkUjgJqFd41Sofa102TAkEvzJpB3LDNZW9KsQG9rGz4E2hZgL+BnehmFhLrTTsO9rTPt5acAki59BVzfWvdvPAP4G+Ujm6gBiZPnMoRh27tYcfnt4+MLP0PTpCzMqTQQsVoY5hQTOgVwOXfrp1e6MXSP70nAE7YkqQaOWjW1d6kL1W+5CZU31nq+lSYoG79RMxvSvBMv7KxjyVHtz+MQWBOyX0R6JmBA+SW2ghoZTMtQ/2NbZ2+OqDUZq0EGJxLQY4jEMaL5IcH+6MEoFII1QVJ/UI6ySR+n9g/nW2UJaq5wSj+7CglwUE3HZXAZHAyUdaSuBj39Kt1CUIWVauBZILujjtJvpX9qR811kzpe8/YRqn7jYgWlGfp6/IK895UzX6oNn6fhYiPZgprKl8SaMCM102WFTiZ/yF3e7JSdrxg5ofZIKvou7jdLbA1sCMQQmp3I9OT0m+cY3vb5YsFMJ21UCHEBWPRPZKibQKSA1T8ArDSuOcCZPpBTAMAuDiOH2zhuxDTkd2DWjUnKTIpvKnevAkzzbIs03yAg0ai9kjBFSqX1MVLK62pyaVxpPzWmG25tBQNmdkeOJVMJmDp6fLKIi/c2qv3txvy34X1eDOsf10ssAppYvZUIr8mzxy7ZWUS2LzDbgsGCSU5Z6qIUGzMggPIuwePtI2oIi0XvjoPleACYucJmOPzGYVCgEwdi/5cSvaztq8xza7Xdg/h8/b/hw6hOtMQPPlXSeLlR+LysX3QWCAZPiqqe3iLAXDmzzBsunJfwPA+YJSvXOWzdHclcQNx5Wje0arpLusEVkGvPSZtbd/m4UzDG2FuLXSmXiQpj6tqkFhVLum9j+dGKBBvdPPM/PLuMiELdjTXeoTMVAbXXKhPPwQgOm7fL+kO1LgoT2eSzPEym4u62NB/IM/UZk/DOMFFZiU+uvTnjkkDFPZ+wG7jdHM2cw2J8EonLmc/tCGS1r9mT0Ibj7eR2g70hVzLvtZgr/XKSYy8R8SUYsO15dpZ2D4rSh8j/euH/sIRFMZdb6jEbpZmS8rPHgUORkCW/KTn/taNmV4Sf3RDKTzkRQP+ZNvyUA3KkBoDXo2VSVZqupduab0JsFVjxKGYVrtfOBQh/8yZnf0Ais1aJf93peaSKY0reJrQRuL0xAYAQ==
```

### Tool Relationships Table Sample
```sql
SELECT * FROM tool_relationships WHERE session_id = '2ff9e2d5-b271-44a4-bb03-d9c93b066b9f' LIMIT 5;
```
```
id|session_id|parent_uuid|child_uuid|relationship_type|created_at
1|2ff9e2d5-b271-44a4-bb03-d9c93b066b9f|35edb0ad-f59d-4bb1-94de-0c4a85299578|b6a52e42-e99c-466c-b327-5e230031a8d9|parent-child|2025-08-16T17:15:33.584895
2|2ff9e2d5-b271-44a4-bb03-d9c93b066b9f|b6a52e42-e99c-466c-b327-5e230031a8d9|d3516461-e961-46ba-8f6f-3cb044e3b8f1|parent-child|2025-08-16T17:15:33.586082
3|2ff9e2d5-b271-44a4-bb03-d9c93b066b9f|d3516461-e961-46ba-8f6f-3cb044e3b8f1|a399dc96-66f7-449b-b7bf-a266002d0f40|parent-child|2025-08-16T17:15:33.586798
4|2ff9e2d5-b271-44a4-bb03-d9c93b066b9f|a399dc96-66f7-449b-b7bf-a266002d0f40|64c29336-d218-4583-8fe6-529f2788716a|parent-child|2025-08-16T17:15:33.587565
5|2ff9e2d5-b271-44a4-bb03-d9c93b066b9f|64c29336-d218-4583-8fe6-529f2788716a|41927973-b144-49cd-9e73-50387f7a297d|parent-child|2025-08-16T17:15:33.588329
```

### Token Usage Analysis
```sql
SELECT 
    SUM(tokens_total) as total,
    SUM(tokens_input) as input,
    SUM(tokens_output) as output,
    SUM(tokens_cache_read) as cache_read,
    SUM(tokens_cache_create) as cache_create,
    ROUND(100.0 * SUM(tokens_cache_read) / NULLIF(SUM(tokens_total), 0), 2) as cache_hit_rate
FROM transcript_events
WHERE session_id = '2ff9e2d5-b271-44a4-bb03-d9c93b066b9f';
```
```
total: 39,938,482
input: 34,157
output: 146,004
cache_read: 36,272,791
cache_create: 3,485,530
cache_hit_rate: 90.82%
```

## 10. Data Enhancement Status

### Fields Now Captured (After Enhancement)
- ✅ `transcript_path` - Added to all hook events
- ✅ `git_branch` - Extracted and stored
- ✅ `stop_hook_active` - Captured in Stop events
- ✅ `token_usage` - Full usage statistics from responses
- ✅ `duration_ms` - Extracted from totalDurationMs
- ✅ `model/service_tier` - Populated from responses
- ✅ `thinking` - Claude's reasoning process captured
- ✅ `uuid/parent_uuid` - Full relationship tracking

### Tools Created
1. **`verify_hook_data.py`** - Verifies hook data completeness
2. **`parse_transcript.py`** - Extracts rich data from transcripts

### Database Schema Additions
- 3 new tables: `transcript_events`, `thinking_logs`, `tool_relationships`
- 22+ new fields for comprehensive tracking
- Full UUID-based relationship mapping
- Token usage and cost tracking capabilities

## Notes

- All timestamps are in ISO 8601 format with microsecond precision
- JSON fields are stored as strings in SQLite
- Session IDs are UUIDs
- File paths are absolute paths on the local system
- The hook system uses stdin/stdout for data passing between Claude and Python scripts
- Transcript files contain 144+ fields not available in hooks
- Token usage can reach millions per session (39.9M in example)
- Cache efficiency is critical for cost management (90%+ hit rate achievable)