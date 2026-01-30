# Changelog

All notable changes to Lazarus will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- Configuration system with Pydantic models and JSON Schema validation
- Core healing loop with retry logic and timeout enforcement
- Claude Code CLI integration for AI-powered fixes
- Context builder with stdout/stderr capture, git history, and system info
- Secrets redactor with configurable patterns
- Script runner with success criteria verification
- PR creation via `gh` CLI
- Notification system (Slack, Discord, Email, GitHub Issues, webhooks)
- Structured JSON logging with rotation
- CLI commands: `heal`, `run`, `history`, `validate`, `init`, `check`
- GitHub Actions workflow templates
- Self-hosted runner setup guides for macOS and Linux
- Example scripts demonstrating various failure scenarios
- Comprehensive test suite

### Security
- Automatic redaction of secrets and sensitive data before AI analysis
- Configurable redaction patterns
- No external data storage

## [0.1.0] - Unreleased

Initial release.
