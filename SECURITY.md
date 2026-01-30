# Security Policy

## Supported Versions

The following versions of Lazarus are currently being supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

As the project matures, we will extend support to multiple versions. For now, we recommend always using the latest release.

---

## Reporting a Vulnerability

We take the security of Lazarus seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, please report security issues via one of these methods:

1. **GitHub Security Advisories** (Preferred):
   - Go to the [Security tab](https://github.com/yourusername/lazarus/security/advisories)
   - Click "Report a vulnerability"
   - Fill out the advisory form with details

2. **Email**:
   - Send an email to: security@yourdomain.com
   - Use PGP encryption if possible (key available on request)
   - Include "LAZARUS SECURITY" in the subject line

### What to Include

When reporting a vulnerability, please include:

- **Description**: Clear description of the vulnerability
- **Impact**: What an attacker could do with this vulnerability
- **Reproduction**: Step-by-step instructions to reproduce the issue
- **Affected versions**: Which versions are affected
- **Suggested fix**: If you have ideas on how to fix it
- **Your contact info**: How we can reach you for follow-up

### Example Report

```
Subject: LAZARUS SECURITY - Secrets Redaction Bypass

Description:
The secrets redaction system can be bypassed by encoding API keys
in base64 format. The regex patterns only match plaintext secrets.

Impact:
An attacker could encode secrets to bypass redaction, causing them
to be sent to Claude API in plaintext.

Reproduction:
1. Create a script with: api_key = base64.b64decode("YWJjMTIz...")
2. Run: lazarus heal script.py --verbose
3. Observe that the base64 string is not redacted

Affected Versions:
0.1.0 and earlier

Suggested Fix:
Add redaction patterns for common encoding schemes (base64, hex, etc.)
or decode common formats before applying redaction patterns.
```

---

## Response Process

When you report a vulnerability:

1. **Acknowledgment** (Within 48 hours):
   - We will acknowledge receipt of your report
   - We may ask for additional information

2. **Assessment** (Within 1 week):
   - We will assess the vulnerability
   - Determine severity and impact
   - Develop a fix timeline

3. **Fix Development** (Timeline depends on severity):
   - Critical: Within 7 days
   - High: Within 30 days
   - Medium: Within 90 days
   - Low: Next scheduled release

4. **Fix Release**:
   - We will release a patch
   - Publish a security advisory
   - Credit you (unless you prefer to remain anonymous)

5. **Public Disclosure**:
   - After the fix is released and users have had time to update (typically 1-2 weeks)
   - We will publish details of the vulnerability

---

## Security Update Policy

### How We Notify Users

Security updates will be announced via:

1. **GitHub Security Advisories**:
   - Visible on the repository security tab
   - Email notifications to repository watchers

2. **Release Notes**:
   - Clearly marked as security releases
   - Detailed in CHANGELOG.md

3. **README Banner** (for critical issues):
   - Prominent notice in README.md
   - Linking to security advisory

### Severity Levels

We use the following severity classification:

- **Critical**: Immediate action required
  - Remote code execution
  - Credential compromise
  - Data exfiltration

- **High**: Update as soon as possible
  - Privilege escalation
  - Secrets leakage
  - Authentication bypass

- **Medium**: Update in normal maintenance cycle
  - Denial of service
  - Information disclosure
  - Configuration weaknesses

- **Low**: Update when convenient
  - Minor information disclosure
  - Edge case vulnerabilities
  - Deprecated functionality

---

## Security Considerations for Users

### What Lazarus Does

Lazarus:
- Sends script content and error context to Claude AI (Anthropic)
- Creates git commits and pull requests on your behalf
- Executes scripts to verify fixes
- May run with elevated permissions if scripts require it

### What You Should Know

1. **Data Sent to External Services**:
   - All context (script, errors, git history) is sent to Anthropic's Claude API
   - See [Security Documentation](docs/security.md) for full details

2. **Automatic Secrets Redaction**:
   - Lazarus attempts to redact secrets automatically
   - This is pattern-based and may not catch all secrets
   - **Always review PRs before merging**

3. **API Key Security**:
   - Use a dedicated Anthropic API key for Lazarus (not your personal key)
   - Set spending limits in [Anthropic Console](https://console.anthropic.com/settings/limits)
   - Rotate keys every 90 days

4. **GitHub Access**:
   - Lazarus requires write access to create branches and PRs
   - Use a service account with minimal permissions
   - Enable branch protection rules

5. **Code Review Required**:
   - **NEVER** auto-merge Lazarus PRs
   - Always require human review
   - Watch for malicious code or leaked secrets

### Recommended Security Practices

1. **Start with draft PRs**:
   ```yaml
   git:
     draft_pr: true
   ```

2. **Limit file access**:
   ```yaml
   scripts:
     - name: my-script
       allowed_files:
         - "scripts/**/*.py"
       forbidden_files:
         - "**/*.env"
         - "secrets/**"
   ```

3. **Restrict tools**:
   ```yaml
   healing:
     allowed_tools:
       - Edit
       - Read
     forbidden_tools:
       - Bash  # Prevent command execution
   ```

4. **Use separate environments**:
   - Test in staging first
   - Separate API keys per environment
   - Different service accounts

See [Security Documentation](docs/security.md) for comprehensive guidance.

---

## Known Security Limitations

We want to be transparent about Lazarus's security limitations:

1. **Pattern-Based Redaction**:
   - May not catch all secret formats
   - Cannot detect semantic secrets (e.g., "the password is hunter2")
   - Ineffective against encoded secrets (base64, hex, etc.)

2. **AI-Generated Code**:
   - Claude may generate insecure code
   - No automatic security scanning of generated code
   - Requires human review

3. **External Dependencies**:
   - Relies on Claude API (external service)
   - Relies on GitHub CLI (external tool)
   - Vulnerabilities in dependencies

4. **Subprocess Execution**:
   - Scripts run with user permissions
   - No sandboxing of script execution
   - Potential for privilege escalation if scripts are malicious

5. **Git History**:
   - Commits and PRs are permanent
   - Cannot remove secrets once pushed
   - Requires manual intervention to clean history

**Mitigation**: Always review PRs, limit permissions, use draft PRs by default.

---

## Security Disclosure Policy

### Our Commitments

We commit to:

1. **Acknowledge** all security reports within 48 hours
2. **Provide updates** at least weekly during investigation
3. **Credit reporters** in security advisories (if desired)
4. **Not pursue legal action** against researchers who:
   - Report vulnerabilities responsibly
   - Do not exploit vulnerabilities
   - Do not access/modify user data
   - Follow coordinated disclosure

### Coordinated Disclosure

We prefer coordinated disclosure:

1. **Report** the vulnerability privately
2. **Work with us** to understand and fix it
3. **Wait** for the fix to be released
4. **Publish** details after users have had time to update (typically 1-2 weeks)

We will work with you to determine an appropriate disclosure timeline.

---

## Bug Bounty Program

We do not currently have a formal bug bounty program. However:

- We greatly appreciate security research
- We will credit researchers in advisories
- We may provide swag or recognition

As the project grows, we may establish a formal bug bounty program.

---

## Security Hall of Fame

We thank the following researchers for responsibly disclosing security issues:

<!-- When vulnerabilities are reported, we will list researchers here -->

*No vulnerabilities reported yet. Be the first!*

---

## Contact

For security issues:
- **GitHub Security Advisories**: https://github.com/yourusername/lazarus/security/advisories
- **Email**: security@yourdomain.com
- **PGP Key**: Available on request

For general questions:
- **GitHub Issues**: https://github.com/yourusername/lazarus/issues
- **GitHub Discussions**: https://github.com/yourusername/lazarus/discussions

---

## Additional Resources

- [Security Documentation](docs/security.md) - Comprehensive security guide
- [Configuration Reference](docs/configuration.md) - Secure configuration options
- [Troubleshooting](docs/troubleshooting.md) - Security-related issues
- [Architecture](docs/architecture.md) - System security design

---

## Version History

| Date | Version | Security Changes |
|------|---------|------------------|
| 2026-01-30 | 0.1.0 | Initial release with automatic secrets redaction |

---

*This security policy is based on industry best practices and may be updated periodically. Check back for the latest version.*
