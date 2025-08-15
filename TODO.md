# TODO - Technical Debt & Future Enhancements

## Maintainability Assessment Summary
- **Overall Score**: 7.2/10
- **Code Quality**: 7.5/10  
- **Documentation**: 8.5/10
- **Structure**: 8.0/10
- **Dependencies**: 5.0/10
- **Testing**: 4.0/10

---

## 🔴 CRITICAL - Security & Dependencies (Week 1)

### 1. Security Vulnerabilities
**Impact**: Critical | **Effort**: 2-3 days

- **Command Injection Risks**
  - Location: Shell script execution throughout codebase
  - Fix: Add input validation and sanitization
  - Use subprocess with shell=False where possible

- **Path Traversal Vulnerabilities**  
  - Location: File operations in hooks/ and tools/
  - Fix: Validate and sanitize all file paths
  - Implement proper access controls

### 2. Missing Dependency Management
**Impact**: High | **Effort**: 1 day

- **No requirements.txt or pyproject.toml**
  - Create requirements.txt with:
    ```
    tabulate>=0.9.0
    # Add other discovered dependencies
    ```
  - Update setup.sh to check and install dependencies
  - Add virtual environment setup instructions

---

## 🟡 HIGH PRIORITY - Core Functionality (Weeks 2-3)

### 3. Testing Coverage (Current: 4.0/10)
**Impact**: High | **Effort**: 1 week

- **Critical Gaps**:
  - No tests for agent discovery algorithm
  - No tests for hook installation/uninstallation
  - No tests for logging functionality
  - No integration tests for pipeline workflow
  - Only 1 test file: `test_uninstall.py`

- **Action Items**:
  - Create `tests/` directory structure
  - Add unit tests for core modules
  - Add integration tests for full pipeline
  - Target 80% coverage minimum

### 4. Code Duplication
**Impact**: Medium-High | **Effort**: 3-4 days

- **Database Initialization** (2 locations)
  - `/hooks/log_agent_invocation.py` (lines 26-81)
  - `/hooks/log_session.py` (lines 25-43)
  - Fix: Extract to shared database utility module

- **Path Setup Pattern** (7 files)
  - All hooks/ and tools/ Python files
  - Pattern: `PROJECT_DIR / "logs" / "agent_workflow.db"`
  - Fix: Create shared configuration module

- **Database Connections** (23+ occurrences)
  - Repetitive `sqlite3.connect(DB_PATH)` pattern
  - Fix: Create database context manager

- **Color Definitions** (3 shell scripts)
  - `install-logging.sh`, `uninstall-logging.sh`, `setup.sh`
  - Fix: Extract to shared shell utility

### 5. State Persistence & Recovery
**Impact**: High | **Effort**: 3-4 days

- **Current Issue**: No state persistence between interruptions
- **Solution**:
  - Implement checkpoint system for long-running operations
  - Add recovery mechanism for interrupted workflows
  - Store intermediate results in database

---

## 🟠 MEDIUM PRIORITY - Architecture & Quality (Weeks 4-6)

### 6. Parallel Execution Architecture
**Impact**: Medium | **Effort**: 1 week

- **Current**: Sequential execution despite parallel design
- **Issues**:
  - File-based discovery (reading 19 files per invocation)
  - No async task queue
  - Limited scalability

- **Solutions**:
  - Implement proper async with Celery/RQ
  - Create agent registry service
  - Add caching layer for agent discovery

### 7. Error Handling Improvements
**Impact**: Medium | **Effort**: 2-3 days

- **Generic Exception Handling**
  - Location: `/hooks/voice_notifier.py` and others
  - Current: `except Exception as e:`
  - Fix: Catch specific exceptions

- **Missing JSON Error Handling**
  - Location: `/tools/tail_logs.py`
  - Fix: Add fallback for malformed JSON

- **Shell Script Error Handling**
  - Add validation for prerequisites
  - Improve error messages and recovery

### 8. Configuration Management
**Impact**: Medium | **Effort**: 3-4 days

- **Scattered Configuration**
  - Hardcoded paths throughout codebase
  - No validation for configuration values
  - Multiple configuration locations

- **Solutions**:
  - Create centralized config service
  - Use environment variables
  - Add schema validation for YAML frontmatter
  - Consolidate settings management

### 9. Large Script Refactoring
**Impact**: Medium | **Effort**: 2 days

- **install-logging.sh** (400+ lines)
  - Break into smaller functions
  - Extract configuration logic
  
- **setup.sh** (monolithic script)
  - Create functions for git, agents, config
  - Improve modularity

---

## 🟢 LOW PRIORITY - Enhancements (Future)

### 10. Conversation Tracking Across Resume Sessions

**Problem**: When closing and resuming Claude Code conversations, each resume creates a new session in the logs, making it difficult to track work that spans multiple sessions.

**Solution**: Add conversation-level tracking that links related sessions together.

### Implementation Ideas

1. **Database Schema Enhancement**
   - Add `conversation_id` field to sessions table
   - Link sessions based on:
     - Same project directory
     - Resume source indicator
     - Transcript path pattern
     - Time proximity (sessions within X hours)

2. **New Tool: `track_conversation.py`**
   ```bash
   # View current conversation across all resumes
   python3 tools/track_conversation.py --current
   
   # List all conversations in project
   python3 tools/track_conversation.py --list
   
   # Show specific conversation timeline
   python3 tools/track_conversation.py --id <conversation_id>
   ```

3. **Enhanced Analytics**
   - Update `analyze_workflow.py` to support `--conversation` flag
   - Show aggregated stats across entire conversations
   - Track patterns that span multiple work sessions
   - Total time spent on a conversation thread

4. **Query Improvements**
   - Add to `query_logs.py`:
     - `--group-by-conversation` flag
     - `--conversation <id>` to filter by conversation
   - Show both session-level and conversation-level views

### Technical Details

- Sessions with `"source": "resume"` in metadata are continuations
- Use transcript_path to definitively link related sessions
- Consider creating a conversations table for metadata
- Could analyze transcript files for even deeper linking

### Benefits

- Track total time spent on a feature/bug across multiple days
- See agent usage patterns for entire workflows
- Better understand how work progresses across sessions
- More accurate time tracking for project management

### 11. Plugin System for Custom Agents
**Impact**: Low | **Effort**: 1 week

- Create plugin architecture for user-defined agents
- Support external agent repositories
- Dynamic agent loading without restart

### 12. Performance Optimizations
**Impact**: Low | **Effort**: 3-4 days

- Add caching for frequently accessed data
- Optimize database queries
- Implement lazy loading for agent discovery

### 13. Enhanced Monitoring
**Impact**: Low | **Effort**: 3-4 days

- Real-time dashboard for pipeline status
- Metrics collection (Prometheus/Grafana)
- Performance profiling tools

---

## ⚡ Quick Wins (Can be done immediately)

### Immediate Fixes (< 1 hour each)
1. **Create requirements.txt**
   ```bash
   echo "tabulate>=0.9.0" > requirements.txt
   ```

2. **Add .gitignore entries**
   - Add `*.pyc`, `__pycache__/`, `.venv/`
   - Exclude sensitive logs

3. **Fix hardcoded paths** 
   - Replace hardcoded `~/.claude/` with environment variable
   - Use `Path.home()` instead of assuming paths

4. **Add type hints**
   - Start with core modules in tools/
   - Improves IDE support and catches bugs

5. **Extract color definitions**
   - Create `scripts/shared/colors.sh`
   - Source in all shell scripts

---

## Architecture Decision Records Needed

1. **ADR-001**: Service-oriented architecture for core components
2. **ADR-002**: Async task execution framework selection
3. **ADR-003**: Database migration strategy (SQLite → PostgreSQL)
4. **ADR-004**: Configuration management approach
5. **ADR-005**: Security validation framework
6. **ADR-006**: Testing strategy and coverage goals
7. **ADR-007**: Plugin system architecture

---

## Notes

- Priority levels based on impact to production readiness
- Timeline estimates assume single developer
- Critical items block production deployment
- Quick wins can be done between larger tasks
- Consider creating a `shared/` directory for common utilities