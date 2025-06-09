# Claude Code: Complete Guide

Claude Code is an agentic coding tool that lives in your terminal, understands your codebase, and helps you code faster through natural language commands.

## Table of Contents
- [Programmatic Mode (-p)](#programmatic-mode--p)
- [CLI Commands & Flags](#cli-commands--flags)
- [Slash Commands](#slash-commands)
- [Core Capabilities](#core-capabilities)
- [Use Cases & Examples](#use-cases--examples)
- [Configuration & Setup](#configuration--setup)

## Programmatic Mode (-p)

### What is Programmatic Mode?
Programmatic mode allows you to run Claude Code non-interactively with the `-p` flag. Perfect for automation, CI/CD pipelines, and scripting.

### Basic Usage
```bash
# Basic one-off query
claude -p "your query here"

# Pipe content to Claude
cat file.txt | claude -p "explain this code"

# With output formatting
claude -p "fix bugs in this file" --output-format json
```

### Key Features (Version 1.0.16+)
- **Sub-task tracking**: Messages now include `parent_tool_use_id` for better task relationship tracking
- **Structured output**: JSON formatting for machine processing
- **Non-interactive execution**: Perfect for automation

### When to Use Programmatic Mode

#### ✅ Ideal For:
- **CI/CD Pipelines**: Automated testing, linting, security checks
- **Batch Processing**: Bulk file operations, refactoring
- **Scripts & Automation**: Integration with deployment workflows
- **Git Hooks**: Pre-commit checks, automated commit messages
- **Monitoring**: Regular code quality assessments

#### ❌ Not Ideal For:
- **Interactive Development**: Use regular Claude Code REPL instead
- **Complex Multi-step Tasks**: Better suited for interactive mode
- **Learning/Exploration**: Interactive mode provides better feedback

### Examples

#### Automation & CI/CD
```bash
# Test automation
claude -p "run tests and fix any failures" --max-turns 5

# Code quality checks
claude -p "lint the codebase and auto-fix issues" --verbose

# Security scanning
claude -p "check for security vulnerabilities in dependencies"
```

#### Code Analysis
```bash
# Bug detection
cat suspicious_file.py | claude -p "find potential bugs"

# Performance analysis
claude -p "analyze performance bottlenecks in src/" --output-format json

# Code review
claude -p "review this PR for style and logic issues"
```

#### Batch Operations
```bash
# Mass refactoring
claude -p "convert all JavaScript files to TypeScript"

# Documentation generation
claude -p "generate JSDoc comments for all public functions"

# Dependency updates
claude -p "update all deprecated npm packages"
```

#### Git Workflows
```bash
# Smart commit messages
git add . && claude -p "create a commit message for staged changes"

# Changelog generation
claude -p "generate changelog from commits since last release"

# Merge conflict resolution
claude -p "resolve merge conflicts in src/main.js"
```

## CLI Commands & Flags

### Core Commands
```bash
claude                    # Start interactive REPL
claude "initial query"    # Start REPL with prompt
claude -p "query"        # Programmatic mode
claude update            # Update to latest version
claude mcp               # Configure MCP servers
```

### Essential Flags
```bash
--print/-p "query"           # Programmatic mode
--output-format FORMAT      # text/json/stream-json
--verbose                    # Detailed logging
--max-turns N               # Limit agentic turns
--model MODEL_NAME          # Select AI model
--resume                    # Restore previous session
--allowedTools TOOLS        # Specify permitted tools
--disallowedTools TOOLS     # Block specific tools
```

### Examples with Flags
```bash
# JSON output with limited turns
claude -p "optimize this function" --output-format json --max-turns 3

# Verbose logging for debugging
claude -p "debug connection issues" --verbose

# Specific model selection
claude -p "review code quality" --model claude-3-sonnet

# Tool restrictions for security
claude -p "analyze code" --disallowedTools bash,write
```

## Slash Commands

### Account & Session Management
- `/login` - Authenticate with Anthropic
- `/logout` - Sign out
- `/clear` - Clear conversation history
- `/resume` - Restore previous session
- `/cost` - Show token usage and costs

### Configuration
- `/config` - Modify settings
- `/model` - Change AI model
- `/vim` - Enable Vim keybindings
- `/init` - Initialize new project

### Development Tools
- `/review` - Request code review
- `/memory` - Edit memory files
- `/bug` - Report issues
- `/help` - Show usage guide

### Quick Features
- `#` prefix for quick memory
- Multiline input support
- Terminal line break configurations

## Core Capabilities

### 🔧 Code Interaction
- **File Editing**: Modify files across entire codebase
- **Code Understanding**: Explain complex algorithms and architecture
- **Project Context**: Automatically understands project structure
- **Cross-file Analysis**: Trace dependencies and relationships

### 🚀 Development Workflow
- **Test Automation**: Run, debug, and fix tests
- **Git Operations**: Commits, PRs, merge conflict resolution
- **Build Systems**: Execute and troubleshoot build processes
- **Linting & Formatting**: Code quality improvements

### 🌐 External Integration
- **Web Search**: Find documentation and resources
- **Package Management**: Update dependencies, resolve conflicts
- **Database Operations**: Query and migrate databases
- **API Integration**: Test and debug API calls

### 🏗️ Architecture & Planning
- **System Design**: Plan and implement new features
- **Refactoring**: Modernize legacy code
- **Performance**: Identify and fix bottlenecks
- **Security**: Vulnerability assessment and fixes

## Use Cases & Examples

### Daily Development
```bash
# Start your day
claude "review recent commits and suggest improvements"

# During development
claude "implement user authentication with JWT"

# Code review
claude "review this PR and check for edge cases"

# Debugging
claude "fix the failing tests in test/auth.spec.js"
```

### DevOps & Automation
```bash
# Deployment preparation
claude -p "ensure all tests pass before deployment" --max-turns 10

# Infrastructure as code
claude "write Terraform config for AWS ECS deployment"

# Monitoring setup
claude "add logging and monitoring to the payment service"
```

### Learning & Exploration
```bash
# Understand new codebase
claude "explain the architecture of this microservices project"

# Learn new technologies
claude "convert this React class component to hooks"

# Best practices
claude "refactor this code following SOLID principles"
```

## Configuration & Setup

### Installation
```bash
npm install -g @anthropic-ai/claude-code
claude login
```

### Project Initialization
```bash
cd your-project
claude /init
# This creates .claude/ directory with project-specific settings
```

### MCP (Model Context Protocol) Setup
```bash
claude mcp
# Configure external tools and services
```

### Memory Management
```bash
# Quick memory
claude "remember that we use TypeScript strict mode #typescript-config"

# Edit memory files
claude /memory
```

### Enterprise Setup
- **Amazon Bedrock**: Compatible for enterprise environments
- **Google Vertex AI**: Integrated support
- **Security**: Privacy-by-design architecture
- **No External Servers**: Direct API connection

## Advanced Tips

### Performance Optimization
- Use `--max-turns` to limit resource usage
- Leverage `--output-format json` for parsing
- Cache common queries in memory files

### Security Best Practices
- Use `--allowedTools` in production environments
- Review permissions regularly
- Keep Claude Code updated

### Integration Patterns
```bash
# In CI/CD pipeline
if claude -p "validate code quality" --output-format json | jq '.success'; then
  echo "Quality check passed"
  deploy
fi

# Pre-commit hook
claude -p "format and lint staged files" --max-turns 1
```

---

**Version**: Based on Claude Code 1.0.16+  
**Last Updated**: June 2025

For the latest features and updates, run `/release-notes` within Claude Code or visit the [official documentation](https://docs.anthropic.com/en/docs/claude-code).