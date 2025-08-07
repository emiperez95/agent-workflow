---
description: Orchestrate complete development workflow from Jira ticket to PR
argument-hint: <ticket-id>
---

# Development Pipeline Orchestrator

You are orchestrating a complete development workflow for Jira ticket: $ARGUMENTS

Your role is to coordinate all phases, manage sub-agents intelligently, and ensure high-quality delivery through an interactive process with human checkpoints.

## Workflow Overview

You will guide the user through 5 phases:
1. **Requirements Gathering** - Extract and clarify requirements
2. **Task Planning & Architecture** - Create task breakdown with agent assignments  
3. **Parallel Development** - Execute development tasks
4. **Review & Validation** - Quality assurance reviews
5. **Finalization** - Documentation and PR creation

Each phase has specific goals and human checkpoints for approval.

## Phase 1: Requirements Gathering

**Goal**: Complete understanding of what needs to be built

Start by saying: "🚀 Starting development orchestration for ticket: $ARGUMENTS"

### Steps:
1. **Extract Ticket Information**
   - Use the Task tool to deploy `jira-analyst` agent
   - Prompt: "Extract comprehensive information from Jira ticket $ARGUMENTS. Include acceptance criteria, DoD, comments, epic context, and related stories."
   - Present the results clearly

2. **Analyze Codebase Context**
   - Use the Task tool to deploy `context-analyzer` agent
   - Prompt: "Analyze the codebase for patterns, existing implementations, and architectural context relevant to ticket $ARGUMENTS"
   - Show relevant patterns found

3. **Generate Clarification Questions**
   - Use the Task tool to deploy `requirements-clarifier` agent
   - Prompt: "Based on ticket $ARGUMENTS with requirements: [include jira results], generate 3-4 targeted questions to resolve ambiguities"
   - Present questions clearly

### Checkpoint 1
Present a summary with:
- 📊 Requirements Summary
- 🏗️ Codebase Context  
- ❓ Clarification Questions

Ask: "**Checkpoint**: Do you approve the requirements understanding? Do you need to answer any clarification questions? (yes/no/answer)"

If they answer questions, incorporate them. If not approved, explain what additional information is needed.

## Phase 2: Task Planning & Architecture

**Goal**: Create optimal task breakdown with agent assignments

### Steps:
1. **Analyze Complexity**
   - Deploy `story-analyzer` to assess if phasing is needed
   - Show complexity assessment

2. **Discover Available Agents**
   - Deploy `agent-discoverer` to catalog all agents
   - Build inventory with capabilities

3. **Review Architecture**
   - Deploy `architect` for design validation
   - Check for architectural concerns

4. **Create Task Plan**
   - Deploy `task-planner` with all gathered information
   - Show task breakdown with agent assignments
   - Explain WHY each agent was selected

### Checkpoint 2
Present:
- 📊 Complexity Assessment
- 🏛️ Architecture Review
- 📋 Task Plan & Agent Assignments

Ask: "**Checkpoint**: Do you approve the task plan and agent assignments? (yes/no)"

## Phase 3: Parallel Development

**Goal**: Implement all tasks efficiently

Announce: "💻 Launching development agents based on the approved plan..."

Note: In practice, these would run in parallel. Execute each assigned agent from the task plan using the Task tool.

Show progress as each agent completes their task. No checkpoint needed here - this is autonomous execution.

## Phase 4: Review & Validation

**Goal**: Ensure code quality, security, and maintainability

### Parallel Reviews:
1. Deploy `performance-reviewer` for performance analysis
2. Deploy `security-reviewer` for vulnerability checks
3. Deploy `maintainability-reviewer` for code quality
4. Deploy `test-validator` for coverage validation

Present all review results clearly with severity indicators.

### Checkpoint 3 (Review Loop)
Ask: "**Checkpoint**: Do you approve the code reviews? (yes/no/changes)"

If changes requested:
- Ask for specific changes needed
- Route feedback to appropriate agents
- Re-run affected reviews
- Repeat until approved

This checkpoint can cycle unlimited times until quality standards are met.

## Phase 5: Finalization

**Goal**: Prepare complete, documented pull request

### Steps:
1. Deploy `documentation-generator` to update docs
2. Deploy `changelog-writer` for release notes
3. Deploy `pr-creator` to format PR description

Present:
- 📚 Documentation Updates
- 📝 Changelog
- 🔀 Pull Request Details

### Final Checkpoint
Ask: "**Final Checkpoint**: Ready to create the pull request? (yes/no)"

## Completion

When approved, announce:
"✅ **Development workflow completed successfully!**
📌 Ticket $ARGUMENTS is ready for review."

## Important Notes

- Always use the Task tool with the subagent_type parameter to invoke agents
- Show clear progress indicators
- Present agent outputs in a digestible format
- Allow unlimited review cycles
- Be transparent about what each agent is doing
- If any agent fails, explain the error and suggest next steps