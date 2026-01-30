"""Tests for the CLI module."""




def test_cli_app_exists():
    """Test that the CLI app can be imported."""
    from lazarus.cli import app

    assert app is not None
    assert hasattr(app, 'command')


def test_cli_commands_registered():
    """Test that all expected commands are registered."""
    from lazarus.cli import app

    # Get command names from callback function names (Typer doesn't always set cmd.name)
    command_names = [
        cmd.callback.__name__ if cmd.callback else cmd.name
        for cmd in app.registered_commands
    ]

    # Check expected commands
    assert 'heal' in command_names
    assert 'run' in command_names
    assert 'history' in command_names
    assert 'validate' in command_names
    assert 'init' in command_names
    assert 'check' in command_names


def test_create_config_template_minimal():
    """Test minimal config template creation."""
    from lazarus.cli import _create_config_template

    template = _create_config_template(full=False)

    assert 'scripts:' in template
    assert 'healing:' in template
    assert 'max_attempts:' in template
    assert 'Minimal starter template' in template


def test_create_config_template_full():
    """Test full config template creation."""
    from lazarus.cli import _create_config_template

    template = _create_config_template(full=True)

    assert 'scripts:' in template
    assert 'healing:' in template
    assert 'notifications:' in template
    assert 'git:' in template
    assert 'security:' in template
    assert 'logging:' in template
    assert 'Full template with all available options' in template


def test_display_healing_result_success(capsys):
    """Test displaying a successful healing result."""
    from lazarus.cli import _display_healing_result
    from lazarus.core.context import ExecutionResult
    from lazarus.core.healer import HealingResult

    result = HealingResult(
        success=True,
        attempts=[],
        final_execution=ExecutionResult(
            exit_code=0,
            stdout="Success!",
            stderr="",
            duration=1.0,
        ),
        duration=5.0,
    )

    _display_healing_result(result, verbose=False)

    # Note: Rich output is harder to capture, but at least test it doesn't crash


def test_display_healing_result_failure(capsys):
    """Test displaying a failed healing result."""
    from lazarus.cli import _display_healing_result
    from lazarus.core.context import ExecutionResult
    from lazarus.core.healer import HealingResult

    result = HealingResult(
        success=False,
        attempts=[],
        final_execution=ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error occurred",
            duration=1.0,
        ),
        duration=10.0,
        error_message="Failed to heal",
    )

    _display_healing_result(result, verbose=False)

    # Test it doesn't crash


def test_show_config_summary():
    """Test displaying config summary."""
    from lazarus.cli import _show_config_summary
    from lazarus.config.schema import LazarusConfig

    config = LazarusConfig()
    _show_config_summary(config)

    # Test it doesn't crash
