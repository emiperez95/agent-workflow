# 📚 Agent Directory Documentation

This directory contains all the AI agents that power the development pipeline. Each agent is a specialized assistant with specific capabilities and expertise.

## 🗂️ Directory Structure

> **Note**: The directory structure has been flattened for Claude compatibility. All agents are now in the root `agents/` directory.
> 
> **Important**: The `dev-orchestrator` has been converted to a Claude command (`/dev-orchestrator`) for better interactive workflow management.

```
agents/
├── agent-discoverer.md          # Finds available agents
├── architect.md                 # Architecture validator
├── backend-developer.md         # Generic backend
├── changelog-writer.md          # Release documentation
├── context-analyzer.md          # Codebase pattern finder
├── database-developer.md        # Generic database
├── documentation-generator.md   # Documentation updater
├── duplication-checker.md       # Code reuse finder
├── frontend-developer.md        # Generic frontend
├── jira-analyst.md             # Jira ticket analyzer
├── maintainability-reviewer.md  # Code quality reviewer
├── performance-reviewer.md      # Performance analyzer
├── pr-creator.md               # Pull request formatter
├── requirements-clarifier.md    # Question generator
├── security-reviewer.md         # Security validator
├── story-analyzer.md           # Complexity assessor
├── task-planner.md             # Task breakdown creator
├── test-developer.md           # Generic testing
└── test-validator.md           # Coverage validator
```

## 🎯 Agent Types

### 1. Orchestrator (Now a Command)

> **Important**: The `dev-orchestrator` has been converted to a Claude command (`/dev-orchestrator`) for better interactive workflow management. Use `/dev-orchestrator <ticket-id>` to start the development workflow.

The brain of the operation. Manages all phases and coordinates other agents through an interactive workflow with human checkpoints.

### 2. Requirements Agents

Understand what needs to be built:

- Extract information from tickets
- Analyze existing code
- Clarify ambiguities

### 3. Planning Agents

Design the optimal approach:

- Discover available specialists
- Break down complex work
- Validate architecture
- Find reusable code

### 4. Development Agents

Implement the actual code:

- **Generic**: Fallbacks for any technology
- **Specialized**: Your custom, project-specific agents

### 5. Review Agents

Ensure quality and standards:

- Performance optimization
- Security best practices
- Code maintainability
- Test coverage

### 6. Finalization Agents

Prepare for deployment:

- Update documentation
- Create changelogs
- Format pull requests

## 🛠️ Creating Your Own Agents

### Quick Template

````yaml
---
name: your-agent-name
description: Core purpose. Expert in [technologies]. Handles [tasks]. PROACTIVELY USED for [when to use].
tools: cody, file_editor, [additional tools]
---

# Agent Title

## Expertise
- List specific skills
- Technologies mastered
- Patterns understood

## Responsibilities
- What this agent handles
- When it should be used
- What it produces

## Process
1. How it approaches tasks
2. Steps it follows
3. Quality checks

## Code Patterns
```language
// Include actual examples from your project
````

## Best Practices

- Project-specific conventions
- Common patterns to follow
- Anti-patterns to avoid

````

### Naming Conventions

You can name agents anything! The system matches by description content:

- ✅ **Creative names**: `code-ninja`, `bug-hunter`, `style-wizard`
- ✅ **Descriptive names**: `react-specialist`, `api-developer`
- ✅ **Fun names**: `captain-frontend`, `database-wizard`

### Description Best Practices

```yaml
# ❌ Vague description
description: Handles frontend stuff

# ✅ Rich, searchable description
description: React specialist creating performant, accessible components. Expert in TypeScript, Redux Toolkit, React Query, styled-components. Handles component architecture, state management, performance optimization. PROACTIVELY USED for all React UI development.
````

## 📊 Agent Selection Algorithm

The pipeline uses intelligent matching:

1. **Keyword Extraction**: From task description
2. **Description Scanning**: All available agents
3. **Scoring**:
   - Description keyword match: 60 points
   - Technology match: 50 points
   - Capability match: 40 points
   - Generic fallback: 10 points
4. **Selection**: Highest scoring agent wins

## 🔧 Available Tools

Agents can use these tools:

- `cody` - AI code assistance
- `file_editor` - Read/write files
- `bash` - Execute commands
- `npm` - Node package management
- `git` - Version control operations
- `curl` - API testing
- `analysis` - Code analysis
- `rg_search` - Fast code search
- Atlassian tools - Jira/Confluence integration

## 📈 Performance Tips

1. **Specialized > Generic**: Create agents for your specific stack
2. **Rich Descriptions**: More keywords = better matching
3. **Clear Boundaries**: Each agent should have distinct expertise
4. **Iterative Improvement**: Refine based on usage

## 🚀 Getting Started with Custom Agents

1. **Identify Patterns**: What tasks do you do repeatedly?
2. **Create Specialist**: Make an agent for that pattern
3. **Test It**: Run a few tasks through the pipeline
4. **Refine**: Improve based on results
5. **Share**: Help your team be more productive

## 📝 Examples to Copy

Check the `examples/` directory for battle-tested agent configurations you can adapt for your project.

## 🤝 Contributing New Agents

1. Create agent in appropriate directory
2. Test with real tasks
3. Document any special patterns
4. Submit PR with usage examples

---

**Remember**: The best agents are those tailored to YOUR project's specific needs and patterns!
