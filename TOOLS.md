# Agent Tools Reference

This document provides a comprehensive reference for all available tools and their assignments to agents.

## Tool Categories and Available Tools

### Readonly Tools
Basic file system and web operations without modification capabilities.

**Tools:**
- `Glob` - File pattern matching
- `Grep` - Search within files
- `LS` - List directory contents
- `Read` - Read file contents
- `NotebookRead` - Read Jupyter notebooks
- `WebFetch` - Fetch web content
- `TodoWrite` - Manage todo lists
- `WebSearch` - Search the web

### Edit Tools
File modification and creation capabilities.

**Tools:**
- `Edit` - Edit existing files
- `MultiEdit` - Multiple edits in one operation
- `Write` - Write new files
- `NotebookEdit` - Edit Jupyter notebooks

### Execution Tools
Command execution capabilities.

**Tools:**
- `Bash` - Execute shell commands

### Context7 Tools
Library documentation and code examples.

**Tools:**
- `mcp__context7__resolve-library-id` - Resolve library names to IDs
- `mcp__context7__get-library-docs` - Fetch library documentation

### Magic Tools
UI component generation and inspiration.

**Tools:**
- `mcp__magic__21st_magic_component_builder` - Build UI components
- `mcp__magic__logo_search` - Search for logos
- `mcp__magic__21st_magic_component_inspiration` - Get UI inspiration
- `mcp__magic__21st_magic_component_refiner` - Refine UI components

### Playwright Tools
Browser automation and testing.

**Tools:**
- `mcp__playwright__browser_close` - Close browser
- `mcp__playwright__browser_resize` - Resize browser window
- `mcp__playwright__browser_console_messages` - Get console messages
- `mcp__playwright__browser_handle_dialog` - Handle dialogs
- `mcp__playwright__browser_evaluate` - Execute JavaScript
- `mcp__playwright__browser_file_upload` - Upload files
- `mcp__playwright__browser_install` - Install browser
- `mcp__playwright__browser_press_key` - Press keyboard keys
- `mcp__playwright__browser_type` - Type text
- `mcp__playwright__browser_navigate` - Navigate to URL
- `mcp__playwright__browser_navigate_back` - Go back
- `mcp__playwright__browser_navigate_forward` - Go forward
- `mcp__playwright__browser_network_requests` - Get network requests
- `mcp__playwright__browser_take_screenshot` - Take screenshots
- `mcp__playwright__browser_snapshot` - Get accessibility snapshot
- `mcp__playwright__browser_click` - Click elements
- `mcp__playwright__browser_drag` - Drag and drop
- `mcp__playwright__browser_hover` - Hover over elements
- `mcp__playwright__browser_select_option` - Select dropdown options
- `mcp__playwright__browser_tab_list` - List tabs
- `mcp__playwright__browser_tab_new` - Open new tab
- `mcp__playwright__browser_tab_select` - Select tab
- `mcp__playwright__browser_tab_close` - Close tab
- `mcp__playwright__browser_wait_for` - Wait for conditions

### Sequential Thinking Tools
Advanced reasoning and problem-solving.

**Tools:**
- `mcp__sequential-thinking__sequentialthinking` - Chain of thought reasoning

### Atlassian Read Tools
Read operations for Jira and Confluence.

**Tools:**
- `mcp__atlassian__atlassianUserInfo` - Get user info
- `mcp__atlassian__getAccessibleAtlassianResources` - Get accessible resources
- `mcp__atlassian__getConfluenceSpaces` - Get Confluence spaces
- `mcp__atlassian__getConfluencePage` - Get Confluence page
- `mcp__atlassian__getPagesInConfluenceSpace` - Get pages in space
- `mcp__atlassian__getConfluencePageAncestors` - Get page ancestors
- `mcp__atlassian__getConfluencePageFooterComments` - Get footer comments
- `mcp__atlassian__getConfluencePageInlineComments` - Get inline comments
- `mcp__atlassian__getConfluencePageDescendants` - Get page descendants
- `mcp__atlassian__searchConfluenceUsingCql` - Search Confluence
- `mcp__atlassian__getJiraIssue` - Get Jira issue
- `mcp__atlassian__getTransitionsForJiraIssue` - Get issue transitions
- `mcp__atlassian__lookupJiraAccountId` - Lookup account ID
- `mcp__atlassian__searchJiraIssuesUsingJql` - Search Jira issues
- `mcp__atlassian__getJiraIssueRemoteIssueLinks` - Get remote links
- `mcp__atlassian__getVisibleJiraProjects` - Get visible projects
- `mcp__atlassian__getJiraProjectIssueTypesMetadata` - Get issue types

### Atlassian Write Tools
Write operations for Jira and Confluence.

**Tools:**
- `mcp__atlassian__createConfluencePage` - Create Confluence page
- `mcp__atlassian__updateConfluencePage` - Update Confluence page
- `mcp__atlassian__createConfluenceFooterComment` - Create footer comment
- `mcp__atlassian__createConfluenceInlineComment` - Create inline comment
- `mcp__atlassian__editJiraIssue` - Edit Jira issue
- `mcp__atlassian__createJiraIssue` - Create Jira issue
- `mcp__atlassian__transitionJiraIssue` - Transition issue status
- `mcp__atlassian__addCommentToJiraIssue` - Add comment to issue

## Agent Tool Assignments

### Orchestrator
- **dev-orchestrator**
  - Tools: readonly + sequential-thinking
  - Purpose: Coordinate workflow, analyze requirements, manage phases

### Phase 1: Requirements
- **jira-analyst**
  - Tools: readonly + atlassian read + sequential-thinking
  - Purpose: Extract and analyze Jira tickets and requirements
  
- **context-analyzer**
  - Tools: readonly + execution
  - Purpose: Analyze codebase patterns and conventions
  
- **requirements-clarifier**
  - Tools: readonly + sequential-thinking
  - Purpose: Generate clarifying questions and resolve ambiguities

### Phase 2: Planning
- **agent-discoverer**
  - Tools: readonly + execution
  - Purpose: Discover and catalog available agents
  
- **story-analyzer**
  - Tools: readonly + sequential-thinking
  - Purpose: Analyze story complexity and propose phases
  
- **task-planner**
  - Tools: readonly + sequential-thinking
  - Purpose: Create task breakdown and agent assignments
  
- **architect**
  - Tools: readonly + context7
  - Purpose: Review architectural implications
  
- **duplication-checker**
  - Tools: readonly
  - Purpose: Find existing implementations

### Phase 3: Development
- **backend-developer**
  - Tools: readonly + edit + execution + context7
  - Purpose: Implement backend functionality
  
- **frontend-developer**
  - Tools: readonly + edit + execution + context7 + magic
  - Purpose: Implement UI components and frontend logic
  
- **database-developer**
  - Tools: readonly + edit + execution
  - Purpose: Design schemas and write migrations
  
- **test-developer**
  - Tools: readonly + edit + execution + playwright
  - Purpose: Create comprehensive tests

### Phase 4: Review
- **performance-reviewer**
  - Tools: readonly + sequential-thinking
  - Purpose: Analyze performance implications
  
- **security-reviewer**
  - Tools: readonly + sequential-thinking
  - Purpose: Review security vulnerabilities
  
- **maintainability-reviewer**
  - Tools: readonly
  - Purpose: Review code quality and documentation
  
- **test-validator**
  - Tools: readonly + execution + playwright
  - Purpose: Run tests and validate coverage

### Phase 5: Finalization
- **documentation-generator**
  - Tools: readonly + edit
  - Purpose: Update documentation
  
- **changelog-writer**
  - Tools: readonly + edit
  - Purpose: Create changelogs and migration guides
  
- **pr-creator**
  - Tools: readonly + execution
  - Purpose: Create pull requests

## Tool Assignment Rationale

### Security Principles
- **Readonly by default**: All agents have readonly tools for safety
- **Edit permissions**: Only given to agents that create/modify code
- **Execution permissions**: Only for agents that need to run commands
- **Write permissions**: No agent has Atlassian write tools (human approval required)

### Capability Matching
- **Sequential thinking**: For agents requiring complex reasoning
- **Context7**: For agents needing library documentation
- **Magic**: For UI-focused development
- **Playwright**: For testing and browser automation
- **Atlassian read**: Only for requirements gathering

### Phase Alignment
- Early phases (1-2): Mostly readonly + specialized tools
- Development phase (3): Full edit + execution capabilities
- Review phase (4): Readonly + analysis tools
- Finalization phase (5): Limited edit for documentation