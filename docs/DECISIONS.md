# Architectural Decision Records (ADRs)

This document captures key architectural decisions made during the development of Lazarus.

## Table of Contents

- [ADR-001: Use Python as Implementation Language](#adr-001-use-python-as-implementation-language)
- [ADR-002: Use Typer for CLI](#adr-002-use-typer-for-cli)
- [ADR-003: Use Pydantic for Configuration Validation](#adr-003-use-pydantic-for-configuration-validation)
- [ADR-004: Use Claude Code CLI via Subprocess](#adr-004-use-claude-code-cli-via-subprocess)
- [ADR-005: Use gh CLI for PR Creation](#adr-005-use-gh-cli-for-pr-creation)

---

## ADR-001: Use Python as Implementation Language

**Status:** Accepted

**Date:** 2026-01-30

### Context

Lazarus needs to orchestrate complex workflows involving file I/O, subprocess management, YAML/JSON parsing, and integration with external tools. The implementation language should provide good developer experience, rich ecosystem support, and reliable subprocess handling.

### Decision

Use Python 3.12+ as the implementation language.

### Rationale

**Pros:**
- Native YAML and JSON handling with excellent libraries (PyYAML, Pydantic)
- Robust subprocess management with `subprocess` module
- Rich ecosystem for CLI development (Typer, Click)
- Strong typing support with type hints and mypy
- Excellent libraries for configuration validation (Pydantic)
- Wide adoption and familiarity among developers
- Cross-platform compatibility
- Great tooling (ruff, pytest, mypy)

**Cons:**
- Slower execution compared to compiled languages (not a concern for I/O-bound orchestration)
- Requires Python runtime on target systems

### Alternatives Considered

- **Go:** Better performance but less ergonomic YAML/JSON handling, steeper learning curve
- **Node.js:** Good subprocess handling but less type safety, callback complexity
- **Rust:** Best performance but slower development, higher complexity for orchestration tasks

### Consequences

- Users must have Python 3.12+ installed
- Can leverage Python's rich ecosystem for future features
- Development velocity should be high
- Easy to prototype and iterate

---

## ADR-002: Use Typer for CLI

**Status:** Accepted

**Date:** 2026-01-30

### Context

Lazarus needs a user-friendly CLI with subcommands, options, and good help text. The CLI framework should provide modern developer experience, automatic help generation, and shell completion support.

### Decision

Use Typer for building the command-line interface.

### Rationale

**Pros:**
- Modern, type-hint-based API
- Automatic help text generation
- Built-in shell completion support (bash, zsh, fish)
- Excellent error messages
- Built on Click (battle-tested foundation)
- Minimal boilerplate code
- Great documentation and examples
- Active maintenance and community

**Cons:**
- Additional dependency (though lightweight)
- Less flexible than raw argparse for very complex scenarios

### Alternatives Considered

- **Click:** More verbose, less modern API, though very stable
- **argparse:** Standard library, but more boilerplate and less elegant
- **fire:** Very concise but less explicit, harder to document

### Consequences

- Users get shell completion out of the box
- CLI code will be clean and type-safe
- Easy to extend with new commands
- Good user experience with helpful error messages

---

## ADR-003: Use Pydantic for Configuration Validation

**Status:** Accepted

**Date:** 2026-01-30

### Context

Lazarus configuration files (lazarus.yaml) need to be validated against a schema to catch errors early and provide clear error messages. The validation library should support type safety, provide excellent error messages, and enable JSON Schema generation.

### Decision

Use Pydantic v2 for configuration parsing and validation.

### Rationale

**Pros:**
- Excellent type safety with Python type hints
- Clear, detailed validation error messages
- Automatic JSON Schema generation
- Fast performance (Rust core in v2)
- Supports complex validation logic
- Well-documented and widely adopted
- Great IDE support with type hints
- Easy to extend with custom validators

**Cons:**
- Adds a dependency
- Learning curve for advanced features

### Alternatives Considered

- **marshmallow:** Mature but less type-safe, more boilerplate
- **attrs + cattrs:** Good but less validation-focused
- **dataclasses + manual validation:** More code, worse error messages
- **JSON Schema directly:** Less Pythonic, harder to maintain

### Consequences

- Configuration errors will be caught early with clear messages
- Can generate JSON Schema for documentation
- IDE autocomplete for configuration objects
- Easy to add new configuration options with validation

---

## ADR-004: Use Claude Code CLI via Subprocess

**Status:** Accepted

**Date:** 2026-01-30

### Context

Lazarus needs to invoke Claude to make code changes. We can either use the Claude API directly or leverage the existing Claude Code CLI tool.

### Decision

Use Claude Code CLI via subprocess execution rather than Claude API directly.

### Rationale

**Pros:**
- Leverages existing authentication in Claude Code CLI
- No need to manage API keys in Lazarus
- Claude Code CLI handles complex interactions (file reading, editing, tool use)
- Claude Code CLI is actively maintained by Anthropic
- Reduces complexity in Lazarus codebase
- Users already familiar with Claude Code get consistent behavior
- Inherits Claude Code's safety features and guardrails

**Cons:**
- Requires Claude Code CLI to be installed
- Less control over low-level API interactions
- Subprocess overhead (minimal for typical use cases)
- Dependent on Claude Code CLI stability and features

### Alternatives Considered

- **Direct Claude API:** More control but requires reimplementing file operations, auth management, and complex prompting logic
- **Anthropic SDK:** Still requires custom file handling and auth management

### Consequences

- Users must install and authenticate Claude Code CLI
- Lazarus inherits Claude Code's capabilities and limitations
- Simpler codebase focused on orchestration
- Updates to Claude Code CLI benefit Lazarus automatically
- Need to handle Claude Code CLI version compatibility

---

## ADR-005: Use gh CLI for PR Creation

**Status:** Accepted

**Date:** 2026-01-30

### Context

Lazarus needs to create pull requests after Claude makes code changes. We can either use the GitHub API directly, Git operations + API calls, or leverage the GitHub CLI.

### Decision

Use GitHub CLI (`gh`) for PR creation and GitHub operations.

### Rationale

**Pros:**
- Handles GitHub authentication (OAuth, tokens, SSH)
- Well-tested and maintained by GitHub
- Rich feature set for PR operations (labels, reviewers, templates)
- Consistent behavior with GitHub's official tooling
- Works with both GitHub.com and GitHub Enterprise
- Simpler than implementing GitHub API client
- Users may already have gh CLI installed
- Good error messages and documentation

**Cons:**
- Requires gh CLI to be installed
- Additional dependency on external tool
- Less control over API rate limiting

### Alternatives Considered

- **PyGithub/ghapi:** More control but requires auth management and more code
- **Direct REST API:** Most control but most complexity
- **Git + manual API calls:** Fragile and complex

### Consequences

- Users must install and authenticate gh CLI
- PR creation is robust and feature-rich
- Can leverage gh CLI features (templates, reviewers, labels)
- Simpler codebase with less GitHub-specific code
- Need to handle gh CLI version compatibility
