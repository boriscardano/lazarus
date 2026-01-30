"""Command-line interface for Lazarus using Typer and Rich.

This module provides a beautiful, user-friendly CLI for the Lazarus self-healing
script system with rich terminal output, progress bars, and tables.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from lazarus.claude.client import ClaudeCodeClient
from lazarus.config.loader import ConfigError, load_config, validate_config_file
from lazarus.core.context import build_context
from lazarus.core.healer import Healer
from lazarus.core.runner import ScriptRunner
from lazarus.logging.history import HealingHistory, HistoryRecord
from lazarus.logging.logger import LazarusLogger

# Create Typer app
app = typer.Typer(
    name="lazarus",
    help="Self-healing script runner powered by Claude Code",
    add_completion=False,
)

# Create Rich console for beautiful output
console = Console()


@app.command()
def heal(
    script_path: Path = typer.Argument(
        ...,
        help="Path to the script to heal",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    max_attempts: int | None = typer.Option(
        None,
        "--max-attempts",
        "-n",
        help="Maximum healing attempts (overrides config)",
        min=1,
        max=10,
    ),
    timeout: int | None = typer.Option(
        None,
        "--timeout",
        "-t",
        help="Total timeout in seconds (overrides config)",
        min=60,
    ),
    no_pr: bool = typer.Option(
        False,
        "--no-pr",
        help="Skip PR creation even if enabled in config",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Run without making changes (check only)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to lazarus.yaml (auto-detected if not provided)",
    ),
) -> None:
    """Heal a specific script that is failing.

    This command runs the specified script, captures any failures, and uses
    Claude Code to automatically fix the issues. The healing process will:

    1. Run the script to capture the error
    2. Build context (error, git state, system info)
    3. Request a fix from Claude Code
    4. Verify the fix by re-running the script
    5. Retry if needed (up to max_attempts)
    6. Create a PR with the fix (if enabled)

    Example:
        lazarus heal scripts/backup.py
        lazarus heal scripts/deploy.sh --max-attempts 5 --verbose
    """
    try:
        # Load configuration
        config = load_config(config_path)

        # Override config with CLI options
        if max_attempts is not None:
            config.healing.max_attempts = max_attempts
        if timeout is not None:
            config.healing.total_timeout = timeout

        # Show configuration in verbose mode
        if verbose:
            _show_config_summary(config)

        # Dry run check
        if dry_run:
            console.print("[yellow]Dry run mode - no changes will be made[/yellow]")
            return

        # Initialize logger
        logger = LazarusLogger(config.logging)

        # Initialize history manager
        # First try to find existing history directory in parent directories
        history_dir = HealingHistory.find_history_dir()
        if history_dir:
            history_manager = HealingHistory(history_dir)
        else:
            # Create new history directory in current location
            history_manager = HealingHistory()

        # Create healer
        healer = Healer(config)

        # Show healing banner
        console.print(
            Panel.fit(
                f"[bold blue]Lazarus Self-Healing System[/bold blue]\n"
                f"Script: {script_path}\n"
                f"Max attempts: {config.healing.max_attempts}\n"
                f"Total timeout: {config.healing.total_timeout}s",
                border_style="blue",
            )
        )

        # Log healing start
        logger.log_healing_start(
            script_path=script_path,
            max_attempts=config.healing.max_attempts,
            timeout=config.healing.total_timeout,
        )

        # Run healing with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running healing process...", total=None)

            result = healer.heal(script_path)

            progress.remove_task(task)

        # Log healing completion
        logger.log_healing_complete(script_path=script_path, result=result)

        # Record in history
        record_id = history_manager.record(result=result, script_path=script_path)
        if verbose:
            console.print(f"[dim]History record: {record_id}[/dim]")

        # Display results
        _display_healing_result(result, verbose=verbose)

        # Exit with appropriate code
        sys.exit(0 if result.success else 1)

    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        sys.exit(2)
    except FileNotFoundError as e:
        console.print(f"[red]File not found:[/red] {e}")
        sys.exit(2)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(3)


@app.command()
def run(
    script_path: Path = typer.Argument(
        ...,
        help="Path to the script to run",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    max_attempts: int | None = typer.Option(
        None,
        "--max-attempts",
        "-n",
        help="Maximum healing attempts if script fails",
        min=1,
        max=10,
    ),
    timeout: int | None = typer.Option(
        None,
        "--timeout",
        "-t",
        help="Total timeout in seconds",
        min=60,
    ),
    no_pr: bool = typer.Option(
        False,
        "--no-pr",
        help="Skip PR creation even if enabled in config",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to lazarus.yaml",
    ),
) -> None:
    """Run a script and heal it if it fails.

    This command is similar to 'heal' but provides a friendlier interface
    for just running a script. If the script succeeds, no healing is performed.

    Example:
        lazarus run scripts/backup.py
        lazarus run scripts/deploy.sh --verbose
    """
    # This is essentially an alias for heal
    # We call the heal function directly
    heal(
        script_path=script_path,
        max_attempts=max_attempts,
        timeout=timeout,
        no_pr=no_pr,
        dry_run=False,
        verbose=verbose,
        config_path=config_path,
    )


@app.command()
def history(
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Number of recent healing sessions to show",
        min=1,
        max=100,
    ),
    script: str | None = typer.Option(
        None,
        "--script",
        "-s",
        help="Filter by script name or path",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON",
    ),
) -> None:
    """View healing history.

    Shows recent healing sessions with success/failure status, duration,
    and number of attempts.

    Example:
        lazarus history
        lazarus history --limit 20 --script backup.py
        lazarus history --json > history.json
    """
    try:
        # Initialize history manager
        # First try to find existing history directory in parent directories
        history_dir = HealingHistory.find_history_dir()
        if history_dir:
            history_manager = HealingHistory(history_dir)
        else:
            # Create new history directory in current location
            history_manager = HealingHistory()

        # Get history records
        records = history_manager.get_history(limit=limit, script_filter=script)

        if not records:
            console.print("[yellow]No healing history found[/yellow]")
            sys.exit(0)

        # JSON output
        if json_output:
            output = json.dumps([record.to_dict() for record in records], indent=2)
            console.print(output)
            sys.exit(0)

        # Display as rich table
        _display_history_table(records)
        sys.exit(0)

    except Exception as e:
        console.print(f"[red]Error retrieving history:[/red] {e}")
        sys.exit(1)


@app.command()
def validate(
    config_path: Path | None = typer.Argument(
        None,
        help="Path to lazarus.yaml (auto-detected if not provided)",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed validation output",
    ),
) -> None:
    """Validate lazarus.yaml configuration file.

    Checks the configuration file for syntax errors, missing required fields,
    and validates all settings against the schema.

    Example:
        lazarus validate
        lazarus validate config/lazarus.yaml --verbose
    """
    try:
        # If no path provided, search for config
        if config_path is None:
            from lazarus.config.loader import find_config_file

            config_path = find_config_file()
            if config_path is None:
                console.print(
                    "[red]No lazarus.yaml found in current directory or parents[/red]"
                )
                console.print(
                    "\nRun [bold]lazarus init[/bold] to create a configuration file."
                )
                sys.exit(1)

        # Validate the configuration
        is_valid, errors = validate_config_file(config_path)

        if is_valid:
            console.print(
                Panel.fit(
                    f"[bold green]Configuration is valid![/bold green]\n"
                    f"File: {config_path}",
                    border_style="green",
                )
            )
            sys.exit(0)
        else:
            console.print(
                Panel.fit(
                    f"[bold red]Configuration validation failed[/bold red]\n"
                    f"File: {config_path}",
                    border_style="red",
                )
            )
            console.print("\n[bold]Errors:[/bold]")
            for error in errors:
                console.print(f"  [red]•[/red] {error}")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error validating configuration:[/red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(2)


@app.command()
def init(
    full: bool = typer.Option(
        False,
        "--full",
        help="Create full configuration template with all options",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path (default: ./lazarus.yaml)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing configuration file",
    ),
) -> None:
    """Create a lazarus.yaml configuration template.

    Creates a starter configuration file with sensible defaults. Use --full
    to generate a comprehensive template with all available options.

    Example:
        lazarus init
        lazarus init --full --output config/lazarus.yaml
        lazarus init --force  # Overwrite existing config
    """
    # Determine output path
    if output is None:
        output = Path.cwd() / "lazarus.yaml"

    # Check if file exists
    if output.exists() and not force:
        console.print(f"[red]File already exists:[/red] {output}")
        console.print("Use --force to overwrite")
        sys.exit(1)

    # Create template
    template = _create_config_template(full=full)

    # Write to file
    try:
        output.write_text(template)
        console.print(
            Panel.fit(
                f"[bold green]Configuration created![/bold green]\n"
                f"File: {output}\n\n"
                f"Edit this file to configure your scripts and settings.\n"
                f"Run [bold]lazarus validate[/bold] to check your configuration.",
                border_style="green",
            )
        )
        sys.exit(0)
    except OSError as e:
        console.print(f"[red]Failed to write configuration:[/red] {e}")
        sys.exit(2)


@app.command()
def diagnose(
    script_path: Path = typer.Argument(
        ...,
        help="Path to the script to diagnose",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file",
    ),
) -> None:
    """Diagnose a failing script without making changes.

    Analyzes the script error and shows what Claude thinks is wrong,
    without modifying any files. Useful for review before healing.

    Example:
        lazarus diagnose scripts/backup.py
        lazarus diagnose broken.py --verbose
    """
    try:
        # Load configuration
        config = load_config(config_path)

        # Show configuration in verbose mode
        if verbose:
            _show_config_summary(config)

        # Show diagnosis banner
        console.print(
            Panel.fit(
                f"[bold blue]Lazarus Script Diagnosis[/bold blue]\n"
                f"Script: {script_path}\n"
                f"Mode: Analysis only (no changes)",
                border_style="blue",
            )
        )

        # Initialize script runner
        runner = ScriptRunner(config)

        # Find script configuration
        script_config = None
        for sc in config.scripts:
            if (
                sc.path.name == script_path.name
                or sc.path.resolve() == script_path.resolve()
            ):
                script_config = sc
                break

        # Run the script to capture the error
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running script to capture error...", total=None)

            timeout = script_config.timeout if script_config else 300
            working_dir = script_config.working_dir if script_config else None

            execution_result = runner.run_script(
                script_path=script_path,
                working_dir=working_dir,
                timeout=timeout,
            )

            progress.remove_task(task)

        # Check if script succeeded
        if execution_result.success:
            console.print(
                Panel.fit(
                    "[bold green]Script executed successfully![/bold green]\n"
                    "No errors to diagnose.",
                    border_style="green",
                )
            )
            sys.exit(0)

        # Show the error
        if verbose:
            console.print("\n[bold]Execution Error:[/bold]")
            console.print(f"Exit code: {execution_result.exit_code}")
            if execution_result.stderr.strip():
                console.print(f"[red]stderr:[/red]\n{execution_result.stderr[:1000]}")
            if execution_result.stdout.strip():
                console.print(f"[dim]stdout:[/dim]\n{execution_result.stdout[:1000]}")
            console.print("")

        # Build context for diagnosis
        context = build_context(
            script_path=script_path,
            result=execution_result,
            config=config,
        )

        # Initialize Claude Code client
        working_dir = (
            script_config.working_dir
            if script_config and script_config.working_dir
            else script_path.parent
        )
        claude_client = ClaudeCodeClient(
            working_dir=working_dir,
            timeout=config.healing.timeout_per_attempt,
        )

        # Check if Claude Code is available
        if not claude_client.is_available():
            console.print(
                "[red]Claude Code CLI is not available.[/red]\n"
                "Please install it first:\n"
                "  npm install -g @anthropic-ai/claude-code\n"
                "Then authenticate with:\n"
                "  claude login"
            )
            sys.exit(2)

        # Request diagnosis from Claude
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Requesting diagnosis from Claude Code...", total=None)

            diagnosis = claude_client.request_diagnosis(context)

            progress.remove_task(task)

        # Display the diagnosis
        if diagnosis.success or diagnosis.explanation:
            console.print(
                Panel.fit(
                    "[bold cyan]Claude's Diagnosis[/bold cyan]",
                    border_style="cyan",
                )
            )
            console.print(diagnosis.explanation or diagnosis.raw_output)

            if verbose and diagnosis.raw_output:
                console.print("\n[dim]--- Raw Output ---[/dim]")
                console.print(diagnosis.raw_output)
        else:
            console.print(
                Panel.fit(
                    f"[bold red]Diagnosis Failed[/bold red]\n"
                    f"Error: {diagnosis.error_message or 'Unknown error'}",
                    border_style="red",
                )
            )
            if verbose and diagnosis.raw_output:
                console.print("\n[dim]--- Raw Output ---[/dim]")
                console.print(diagnosis.raw_output)
            sys.exit(1)

        sys.exit(0)

    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        sys.exit(2)
    except FileNotFoundError as e:
        console.print(f"[red]File not found:[/red] {e}")
        sys.exit(2)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(3)


@app.command()
def check(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed check output",
    ),
) -> None:
    """Check prerequisites (claude, gh, git).

    Verifies that all required tools are installed and available:
    - claude: Claude Code CLI
    - gh: GitHub CLI (for PR creation)
    - git: Git version control

    Example:
        lazarus check
        lazarus check --verbose
    """
    console.print(
        Panel.fit(
            "[bold blue]Checking Lazarus Prerequisites[/bold blue]",
            border_style="blue",
        )
    )

    checks = []

    # Check git
    git_available = shutil.which("git") is not None
    checks.append(("git", git_available, "Git version control"))

    # Check gh
    gh_available = shutil.which("gh") is not None
    checks.append(("gh", gh_available, "GitHub CLI (for PR creation)"))

    # Check claude
    claude_available = shutil.which("claude") is not None
    checks.append(("claude", claude_available, "Claude Code CLI"))

    # Create table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Tool", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Description")

    for tool, available, description in checks:
        status = "[green]✓ Available[/green]" if available else "[red]✗ Missing[/red]"
        table.add_row(tool, status, description)

    console.print(table)

    # Show installation instructions for missing tools
    missing = [tool for tool, available, _ in checks if not available]

    if missing:
        console.print("\n[bold yellow]Installation Instructions:[/bold yellow]")
        for tool in missing:
            if tool == "git":
                console.print(
                    "\n[bold]git:[/bold]\n"
                    "  Visit https://git-scm.com/downloads"
                )
            elif tool == "gh":
                console.print(
                    "\n[bold]gh:[/bold]\n"
                    "  Visit https://cli.github.com/ or:\n"
                    "  macOS: brew install gh\n"
                    "  Linux: See https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
                )
            elif tool == "claude":
                console.print(
                    "\n[bold]claude:[/bold]\n"
                    "  npm install -g @anthropic-ai/claude-code\n"
                    "  Then authenticate: claude login"
                )

        sys.exit(1)
    else:
        console.print("\n[bold green]All prerequisites are available![/bold green]")
        sys.exit(0)


def _display_history_table(records: list[HistoryRecord]) -> None:
    """Display healing history as a rich table.

    Args:
        records: List of HistoryRecord objects to display
    """
    table = Table(title="Healing History", show_header=True, header_style="bold cyan")
    table.add_column("Timestamp", style="dim")
    table.add_column("Script", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Attempts", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("PR URL", style="blue")

    for record in records:
        # Format timestamp
        try:
            dt = datetime.fromisoformat(record.timestamp)
            timestamp = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            timestamp = record.timestamp[:16]

        # Format status
        status = "[green]Success[/green]" if record.success else "[red]Failed[/red]"

        # Format script path (show only filename)
        script_name = Path(record.script_path).name

        # Format duration
        duration = f"{record.duration:.1f}s"

        # Format PR URL (show only if available)
        pr_url = record.pr_url if record.pr_url else ""

        table.add_row(
            timestamp,
            script_name,
            status,
            str(record.attempts_count),
            duration,
            pr_url,
        )

    console.print(table)


def _display_healing_result(result, verbose: bool = False) -> None:
    """Display healing result with rich formatting.

    Args:
        result: HealingResult to display
        verbose: Whether to show detailed output
    """
    if result.success:
        # Success panel
        console.print(
            Panel.fit(
                f"[bold green]Healing Successful![/bold green]\n"
                f"Attempts: {len(result.attempts)}\n"
                f"Duration: {result.duration:.2f}s",
                border_style="green",
            )
        )
    else:
        # Failure panel
        console.print(
            Panel.fit(
                f"[bold red]Healing Failed[/bold red]\n"
                f"Attempts: {len(result.attempts)}\n"
                f"Duration: {result.duration:.2f}s\n"
                f"Error: {result.error_message or 'Unknown'}",
                border_style="red",
            )
        )

    # Show attempts in verbose mode
    if verbose and result.attempts:
        console.print("\n[bold]Healing Attempts:[/bold]")
        for attempt in result.attempts:
            console.print(
                f"\n[cyan]Attempt {attempt.attempt_number}:[/cyan] "
                f"({attempt.duration:.2f}s)"
            )
            if attempt.claude_response.explanation:
                console.print(f"  Claude: {attempt.claude_response.explanation}")
            console.print(f"  Status: {attempt.verification.status}")
            if attempt.claude_response.files_changed:
                console.print(f"  Files changed: {', '.join(attempt.claude_response.files_changed)}")


def _show_config_summary(config) -> None:
    """Show configuration summary.

    Args:
        config: LazarusConfig to summarize
    """
    console.print("\n[bold]Configuration:[/bold]")
    console.print(f"  Scripts: {len(config.scripts)}")
    console.print(f"  Max attempts: {config.healing.max_attempts}")
    console.print(f"  Timeout per attempt: {config.healing.timeout_per_attempt}s")
    console.print(f"  Total timeout: {config.healing.total_timeout}s")
    console.print(f"  Claude model: {config.healing.claude_model}")
    console.print()


def _create_config_template(full: bool = False) -> str:
    """Create configuration template.

    Args:
        full: Whether to create full template with all options

    Returns:
        YAML configuration template as string
    """
    if full:
        # Full template with all options
        return """# Lazarus Self-Healing Configuration
# Full template with all available options

scripts:
  - name: example-script
    path: scripts/example.py
    description: Example script that might fail
    schedule: "0 */6 * * *"  # Every 6 hours
    timeout: 300
    working_dir: null
    allowed_files:
      - "scripts/**/*.py"
      - "config/*.yaml"
    forbidden_files:
      - "secrets.yaml"
      - ".env"
    environment:
      - DATABASE_URL
      - API_KEY
    setup_commands: []
    custom_prompt: null
    idempotent: true
    success_criteria:
      exit_code: 0
      contains: "Success"

healing:
  max_attempts: 3
  timeout_per_attempt: 300
  total_timeout: 900
  claude_model: claude-sonnet-4-5-20250929
  max_turns: 30
  allowed_tools: []
  forbidden_tools: []

notifications:
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"
    on_success: true
    on_failure: true

git:
  create_pr: true
  branch_prefix: lazarus/fix
  draft_pr: false
  auto_merge: false

security:
  additional_patterns: []
  safe_env_vars:
    - PATH
    - HOME
    - USER

logging:
  level: INFO
  console: true
  file: logs/lazarus.log
  rotation: 10
  retention: 10
"""
    else:
        # Minimal template
        return """# Lazarus Self-Healing Configuration
# Minimal starter template

scripts:
  - name: my-script
    path: scripts/example.py
    description: My script that might fail
    timeout: 300

healing:
  max_attempts: 3
  timeout_per_attempt: 300
  total_timeout: 900

git:
  create_pr: true
  branch_prefix: lazarus/fix

logging:
  level: INFO
  console: true
"""


if __name__ == "__main__":
    app()
