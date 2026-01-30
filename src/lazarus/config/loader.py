"""Configuration loading with environment variable expansion."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from lazarus.config.schema import LazarusConfig


class ConfigError(Exception):
    """Configuration loading or validation error."""

    pass


def expand_env_vars(data: Any) -> Any:
    """Recursively expand environment variables in configuration data.

    Supports ${VAR_NAME} and ${VAR_NAME:-default} syntax.

    Args:
        data: Configuration data (dict, list, str, or other)

    Returns:
        Data with environment variables expanded
    """
    if isinstance(data, dict):
        return {key: expand_env_vars(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [expand_env_vars(item) for item in data]
    elif isinstance(data, str):
        # Match ${VAR_NAME} or ${VAR_NAME:-default}
        pattern = r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}"

        def replace_var(match: re.Match[str]) -> str:
            var_name = match.group(1)
            default_value = match.group(3) if match.group(3) is not None else ""

            # Get value from environment, or use default
            value = os.environ.get(var_name)
            if value is None:
                if default_value:
                    return default_value
                # Return the original placeholder if no default and var not found
                # This helps with debugging - user will see what's missing
                return match.group(0)
            return value

        return re.sub(pattern, replace_var, data)
    else:
        return data


def find_config_file(start_path: Path | None = None) -> Path | None:
    """Find lazarus.yaml in current directory or parent directories.

    Args:
        start_path: Starting directory (defaults to current working directory)

    Returns:
        Path to lazarus.yaml if found, None otherwise
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    # Search up to root, checking for lazarus.yaml or lazarus.yml
    while True:
        for filename in ("lazarus.yaml", "lazarus.yml"):
            config_path = current / filename
            if config_path.is_file():
                return config_path

        # Stop at filesystem root
        parent = current.parent
        if parent == current:
            break
        current = parent

    return None


def load_config(path: Path | str | None = None) -> LazarusConfig:
    """Load and validate Lazarus configuration.

    Args:
        path: Path to configuration file. If None, searches for lazarus.yaml
              in current directory and parent directories.

    Returns:
        Validated LazarusConfig object

    Raises:
        ConfigError: If configuration file is not found, cannot be parsed,
                     or fails validation
    """
    # Find or use provided config path
    if path is None:
        config_path = find_config_file()
        if config_path is None:
            raise ConfigError(
                "Configuration file not found. Please create a lazarus.yaml "
                "file in your repository root. See documentation for examples."
            )
    else:
        config_path = Path(path)
        if not config_path.is_file():
            raise ConfigError(
                f"Configuration file not found: {config_path}\n"
                f"Please ensure the file exists and is readable."
            )

    # Load YAML
    try:
        with open(config_path, encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        # Parse YAML error to provide helpful message
        error_msg = str(e)
        if hasattr(e, "problem_mark"):
            mark = e.problem_mark
            raise ConfigError(
                f"Failed to parse {config_path}:\n"
                f"  Line {mark.line + 1}, Column {mark.column + 1}\n"
                f"  {error_msg}"
            ) from e
        else:
            raise ConfigError(
                f"Failed to parse {config_path}: {error_msg}"
            ) from e
    except OSError as e:
        raise ConfigError(
            f"Failed to read {config_path}: {e}"
        ) from e

    if raw_data is None:
        raise ConfigError(
            f"Configuration file is empty: {config_path}\n"
            f"Please add configuration. See documentation for examples."
        )

    # Expand environment variables
    try:
        expanded_data = expand_env_vars(raw_data)
    except Exception as e:
        raise ConfigError(
            f"Failed to expand environment variables in {config_path}: {e}"
        ) from e

    # Validate with Pydantic
    try:
        config = LazarusConfig.model_validate(expanded_data)
    except ValidationError as e:
        # Format validation errors nicely
        error_messages = []
        for error in e.errors():
            location = " -> ".join(str(loc) for loc in error["loc"])
            msg = error["msg"]
            error_messages.append(f"  {location}: {msg}")

        raise ConfigError(
            f"Configuration validation failed for {config_path}:\n"
            + "\n".join(error_messages)
        ) from e

    return config


def load_config_dict(path: Path | str | None = None) -> dict[str, Any]:
    """Load configuration as a dictionary (useful for testing or introspection).

    Args:
        path: Path to configuration file

    Returns:
        Configuration dictionary with environment variables expanded

    Raises:
        ConfigError: If configuration file cannot be loaded
    """
    if path is None:
        config_path = find_config_file()
        if config_path is None:
            raise ConfigError("Configuration file not found")
    else:
        config_path = Path(path)

    try:
        with open(config_path, encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
    except (yaml.YAMLError, OSError) as e:
        raise ConfigError(f"Failed to load {config_path}: {e}") from e

    if raw_data is None:
        return {}

    return expand_env_vars(raw_data)


def validate_config_file(path: Path | str) -> tuple[bool, list[str]]:
    """Validate a configuration file without raising exceptions.

    Args:
        path: Path to configuration file

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    try:
        load_config(path)
        return True, []
    except ConfigError as e:
        return False, [str(e)]
    except Exception as e:
        return False, [f"Unexpected error: {e}"]
