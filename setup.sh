#!/bin/bash

# Claude Development Pipeline Setup Script
# This script helps you quickly set up the development pipeline in your project

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════╗"
echo "║     Claude Development Pipeline Setup     ║"
echo "╚═══════════════════════════════════════════╝"
echo -e "${NC}"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in a git repository
if [ ! -d .git ]; then
    print_warning "Not in a git repository. Initialize one? (y/n)"
    read -r response
    if [[ "$response" == "y" ]]; then
        git init
        print_success "Git repository initialized"
    fi
fi

# Create .claude directory structure
print_info "Creating .claude directory structure..."
mkdir -p .claude/agents/{specialized,project-config}

# Check if agents already exist
if [ -d ".claude/agents" ] && [ "$(ls -A .claude/agents)" ]; then
    print_warning ".claude/agents already contains files. Backup existing? (y/n)"
    read -r response
    if [[ "$response" == "y" ]]; then
        backup_dir=".claude/agents.backup.$(date +%Y%m%d_%H%M%S)"
        mv .claude/agents "$backup_dir"
        mkdir -p .claude/agents/{specialized,project-config}
        print_success "Existing agents backed up to $backup_dir"
    fi
fi

# Clone or copy agents
print_info "How would you like to install the agents?"
echo "1) Clone from GitHub (recommended for updates)"
echo "2) I'll copy them manually"
echo "3) Create symbolic link (for development)"
read -r install_choice

case $install_choice in
    1)
        print_info "Enter the GitHub repository URL (or press Enter for default):"
        read -r repo_url
        repo_url=${repo_url:-"https://github.com/yourusername/claude-dev-pipeline.git"}
        
        # Clone to temp directory
        temp_dir=$(mktemp -d)
        git clone "$repo_url" "$temp_dir/claude-dev-pipeline"
        
        # Copy agents
        cp -r "$temp_dir/claude-dev-pipeline/agents/"* .claude/agents/
        
        # Cleanup
        rm -rf "$temp_dir"
        print_success "Agents installed from repository"
        ;;
    2)
        print_info "Copy the agent files to .claude/agents/"
        print_info "Directory created and ready for your agent files"
        ;;
    3)
        print_info "Enter the path to your claude-dev-pipeline/agents directory:"
        read -r agents_path
        if [ -d "$agents_path" ]; then
            ln -sf "$agents_path"/* .claude/agents/
            print_success "Symbolic links created"
        else
            print_error "Directory not found: $agents_path"
            exit 1
        fi
        ;;
esac

# Create project configuration
print_info "Creating project configuration..."
cat > .claude/project-config.yml << 'EOF'
# Claude Development Pipeline Configuration

# Test coverage threshold (default: 80)
test_coverage_threshold: 80

# PR template location
pr_template_path: .github/pull_request_template.md

# Architecture documentation
architecture_docs_path: docs/architecture

# Development settings
max_parallel_tasks: 4
review_parallel: true
auto_retry_attempts: 2

# Add your project-specific settings here
EOF

print_success "Project configuration created"

# Create example specialized agent
print_info "Would you like to create an example specialized agent? (y/n)"
read -r response
if [[ "$response" == "y" ]]; then
    print_info "What's your primary tech stack?"
    echo "1) React + TypeScript"
    echo "2) Django + Python"
    echo "3) Vue.js"
    echo "4) Node.js + Express"
    echo "5) Other"
    read -r stack_choice
    
    case $stack_choice in
        1)
            cat > .claude/agents/specialized/react-specialist.md << 'EOF'
---
name: react-specialist
description: React expert with TypeScript, hooks, Redux Toolkit, and React Query. Creates performant, accessible components following atomic design. Handles complex state management and optimizations. PROACTIVELY USED for all React development.
tools: cody, file_editor, npm, jest
---

# React Specialist

Your specialized React agent configuration here...
EOF
            print_success "Created react-specialist.md"
            ;;
        2)
            cat > .claude/agents/specialized/django-expert.md << 'EOF'
---
name: django-expert
description: Django specialist with DRF, Celery, and PostgreSQL. Handles models, serializers, viewsets, and Django patterns. Expert in performance optimization and testing. PROACTIVELY USED for all Django development.
tools: cody, file_editor, pip, pytest
---

# Django Expert

Your specialized Django agent configuration here...
EOF
            print_success "Created django-expert.md"
            ;;
        *)
            print_info "Create your own specialized agents in .claude/agents/specialized/"
            ;;
    esac
fi

# Create .gitignore entries
print_info "Adding .claude to .gitignore..."
if [ -f .gitignore ]; then
    if ! grep -q "^.claude/agents/\*\.log$" .gitignore; then
        echo -e "\n# Claude Development Pipeline\n.claude/agents/*.log\n.claude/agents/*.tmp" >> .gitignore
        print_success "Updated .gitignore"
    fi
else
    cat > .gitignore << 'EOF'
# Claude Development Pipeline
.claude/agents/*.log
.claude/agents/*.tmp
EOF
    print_success "Created .gitignore"
fi

# Create initial documentation
print_info "Creating pipeline documentation..."
mkdir -p docs/claude-pipeline

cat > docs/claude-pipeline/quick-start.md << 'EOF'
# Quick Start Guide

## Running the Pipeline

1. Start with a Jira ticket:
   ```
   /agent dev-orchestrator
   ```

2. Follow the guided process through all phases

3. Review and approve at checkpoints

## Creating Custom Agents

1. Create a new file in `.claude/agents/specialized/`
2. Use the template format
3. Test with a real task

## Tips

- Name agents creatively - matching works on descriptions!
- Start with generic agents, create specialists as needed
- Review agent performance in metrics
EOF

print_success "Documentation created in docs/claude-pipeline/"

# Final setup summary
echo -e "\n${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}\n"

print_success "Directory structure created"
print_success "Configuration files ready"
print_success "Documentation initialized"

echo -e "\n${BLUE}📋 Next Steps:${NC}"
echo "1. Review agents in .claude/agents/"
echo "2. Create specialized agents for your tech stack"
echo "3. Run: /agent dev-orchestrator"
echo -e "\n${YELLOW}💡 Tips:${NC}"
echo "- Check docs/claude-pipeline/quick-start.md"
echo "- Customize .claude/project-config.yml"
echo "- Create agents with creative names!"

# Check for common development tools
echo -e "\n${BLUE}🔍 Checking environment...${NC}"
command -v node >/dev/null 2>&1 && print_success "Node.js found" || print_warning "Node.js not found"
command -v python >/dev/null 2>&1 && print_success "Python found" || print_warning "Python not found"
command -v git >/dev/null 2>&1 && print_success "Git found" || print_warning "Git not found"

echo -e "\n${GREEN}Happy coding with Claude! 🚀${NC}\n"
