# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Claude Development Pipeline - an AI-powered development workflow system that orchestrates specialized agents to handle the complete software development lifecycle. The system transforms Jira tickets into production-ready pull requests through 5 coordinated phases with human oversight at critical checkpoints.

## Commands for Development

### Installation and Setup
```bash
# Run the setup script to configure the pipeline in a new project
./setup.sh

# The script will:
# - Create .claude/agents directory structure
# - Set up project configuration
# - Initialize documentation
```

### Using the Development Pipeline
```bash
# Start development workflow from a Jira ticket
/dev-orchestrator <ticket-id>

# The orchestrator will guide through all 5 phases:
# 1. Requirements Gathering
# 2. Task Planning & Architecture  
# 3. Parallel Development
# 4. Review & Validation
# 5. Finalization
```

## Architecture

### Agent System
The pipeline uses a description-based agent matching system where agents are selected based on their capabilities rather than naming conventions. Each agent has:
- **Metadata**: Name, description, tools, model assignment
- **Instructions**: Specific guidance for task execution
- **Tool Access**: Carefully scoped permissions (readonly, edit, execution)

### Phase Structure
1. **Requirements Phase**: Extract from Jira, analyze codebase, clarify ambiguities
2. **Planning Phase**: Discover agents, analyze complexity, create task breakdown
3. **Development Phase**: Parallel execution of implementation tasks
4. **Review Phase**: Parallel quality checks (performance, security, maintainability, testing)
5. **Finalization Phase**: Documentation updates, changelog, PR creation

### Tool Categories
- **Readonly Tools**: File system and web operations (Glob, Grep, LS, Read)
- **Edit Tools**: File modification (Edit, MultiEdit, Write)
- **Execution Tools**: Command execution (Bash)
- **Specialized Tools**: Atlassian (Jira/Confluence), Context7 (docs), Magic (UI), Playwright (testing), Sequential Thinking

### Agent Discovery Algorithm
Agents are matched to tasks through semantic analysis:
1. Extract keywords from task description
2. Score agents based on description matches (60 points), technology matches (50 points), capability matches (40 points)
3. Select highest scoring agent with fallback to generic agents

## Key Agents

### Orchestration
- **dev-orchestrator** (command): Manages entire workflow with human checkpoints

### Requirements & Planning
- **jira-analyst**: Extracts comprehensive Jira information
- **context-analyzer**: Analyzes codebase patterns
- **requirements-clarifier**: Generates clarification questions
- **agent-discoverer**: Catalogs available agents
- **task-planner**: Creates task breakdown with assignments
- **architect**: Validates technical approach

### Development
- **backend-developer**: Generic backend development
- **frontend-developer**: Generic frontend with UI components
- **database-developer**: Schema and migrations
- **test-developer**: Comprehensive test creation

### Review & Finalization
- **performance-reviewer**: Algorithm and query analysis
- **security-reviewer**: Vulnerability scanning
- **maintainability-reviewer**: Code quality checks
- **test-validator**: Coverage verification
- **documentation-generator**: Updates docs
- **changelog-writer**: Release notes
- **pr-creator**: Formats pull requests

## Creating Custom Agents

Place new agents in `agents/` directory with this structure:

```yaml
---
name: your-agent-name
description: What this agent does. Expert in [technologies]. Handles [specific tasks]. PROACTIVELY USED for [when to trigger].
tools: Glob, Grep, LS, Read, [additional tools as needed]
model: sonnet
color: blue
---

# Agent Name

## Expertise
- Specific technologies and frameworks
- Patterns and best practices

## Process
1. How the agent approaches tasks
2. Quality checks performed
3. Output format

## Code Patterns
Include project-specific examples
```

The system will automatically discover and match agents based on their descriptions.